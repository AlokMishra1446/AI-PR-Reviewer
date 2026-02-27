import difflib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from ..agents.critic_agent import CriticAgent
from ..agents.expert_agent import ExpertAgent
from ..agents.rule_agent import RuleAgent
from ..azure.diff_parser import AddedLine, parse_unified_diff
from ..azure.pr_commenter import AzurePRCommenter
from ..azure.pr_fetcher import AzurePRFetcher
from ..azure.pr_url_parser import parse_azure_pr_url
from ..embeddings.retriever import RuleRetriever, prepare_chunks_for_store
from ..rules.chunker import RuleChunk, chunk_rules
from ..rules.pdf_loader import load_all_pdfs
from ..rules.txt_loader import load_all_txt
from ..scoring.scoring_engine import compute_overall_scores
from ..utils.config import load_config


def build_diff_for_file(path: str, base_content: str, target_content: str) -> str:
    base_lines = base_content.splitlines(keepends=True)
    target_lines = target_content.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(base_lines, target_lines, fromfile=path, tofile=path, lineterm="")
    return "\n".join(diff_lines)


def detect_language(path: str) -> str:
    lowered = path.lower()
    if lowered.endswith(".py"):
        return "python"
    if lowered.endswith(".js") or lowered.endswith(".jsx"):
        return "javascript"
    if lowered.endswith(".ts") or lowered.endswith(".tsx"):
        return "typescript"
    if lowered.endswith(".java"):
        return "java"
    if lowered.endswith(".cs"):
        return "csharp"
    if lowered.endswith(".go"):
        return "go"
    return "text"


def chunk_added_lines(added_lines: List[AddedLine], max_chars: int) -> List[str]:
    chunks: List[str] = []
    buffer: List[str] = []
    current_size = 0
    for line in added_lines:
        line_repr = f"{line.file_path}:{line.line_number}: {line.content}"
        size = len(line_repr) + 1
        if buffer and current_size + size > max_chars:
            chunks.append("\n".join(buffer))
            buffer = []
            current_size = 0
        buffer.append(line_repr)
        current_size += size
    if buffer:
        chunks.append("\n".join(buffer))
    return chunks


def postprocess_rule_violations(
    violations: List[Dict[str, Any]],
    line_lookup: Dict[Any, str],
) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for violation in violations:
        rule_id = violation.get("rule_id")
        if rule_id is not None:
            rule_id_str = str(rule_id).strip()
            normalized = rule_id_str.replace("_", "").upper()
            if normalized == "NORULESPROVIDED":
                continue
            if not rule_id_str or rule_id_str.upper() in {"N/A", "NA", "NONE"}:
                violation["rule_id"] = None

        description = violation.get("description") or ""
        lowered = description.lower()
        if (
            "method name" in lowered
            or "function name" in lowered
            or "naming convention" in lowered
            or "casing" in lowered
        ):
            file_path = violation.get("file")
            try:
                line_number = int(violation.get("line_number", 0))
            except (TypeError, ValueError):
                line_number = 0

            code = ""
            if file_path and line_number > 0:
                code = line_lookup.get((file_path, line_number), "")

            if code:
                match = re.search(r"'([^']+)'", description)
                method_name = match.group(1) if match else None
                if method_name and f".{method_name}(" in code:
                    continue

                header = code.strip()
                if header.startswith(
                    (
                        "public ",
                        "private ",
                        "protected ",
                        "internal ",
                        "static ",
                        "async ",
                        "sealed ",
                        "virtual ",
                        "override ",
                    )
                ):
                    cleaned.append(violation)
                    continue
                continue

        cleaned.append(violation)
    return cleaned


async def load_rule_chunks(repo_name: Optional[str]) -> List[RuleChunk]:
    """
    Loads rules with repo-aware fallback:

      - rules/generic/*.pdf|*.txt                (always)
      - rules/repos/<repo_name>/*.pdf|*.txt      (if present)

    This ensures:
      - generic rules always apply
      - repo-specific rules apply when available
    """
    config = load_config()
    rules_root = Path(config.rules.rules_path)
    rules_root.mkdir(parents=True, exist_ok=True)

    generic_dir = rules_root / "generic"
    repo_dir = rules_root / "repos" / (repo_name or "")

    combined_chunks: List[RuleChunk] = []

    def load_dir(dir_path: Path, source_tag: str) -> List[RuleChunk]:
        if not dir_path.exists():
            return []
        pdf_text = load_all_pdfs(dir_path)
        txt_text = load_all_txt(dir_path)
        chunks: List[RuleChunk] = []
        if pdf_text.strip():
            chunks.extend(chunk_rules(pdf_text, source=source_tag, max_chars=1500))
        if txt_text.strip():
            chunks.extend(chunk_rules(txt_text, source=source_tag, max_chars=1500))
        return chunks

    # Always include generic rules
    combined_chunks.extend(load_dir(generic_dir, source_tag="generic"))

    # Include repo-specific rules if they exist
    if repo_name:
        combined_chunks.extend(load_dir(repo_dir, source_tag=f"repo:{repo_name}"))

    return combined_chunks


async def review_pull_request(
    pull_request_id: Optional[int] = None,
    pr_url: Optional[str] = None,
    extra_prompt: Optional[str] = None,
    post_comments: bool = False,
    repository: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Supports two ways to call:
      1) review_pull_request(pull_request_id=123, repository="RepoName")
      2) review_pull_request(pr_url="https://.../_git/RepoName/pullrequest/123")

    Repo-specific coding standards:
      - generic rules always
      - + repo rules if available
    """
    config = load_config()

    # Resolve repo + PR id from URL if provided
    resolved_repo = repository
    resolved_pr_id = pull_request_id

    if pr_url:
        parsed = parse_azure_pr_url(pr_url)
        if resolved_repo is None:
            resolved_repo = parsed.repository
        if resolved_pr_id is None:
            resolved_pr_id = parsed.pull_request_id

    if resolved_pr_id is None:
        raise ValueError("pull_request_id must be provided (or provide pr_url).")

    # If still no repo, fallback to env default (keeps current behavior)
    if not resolved_repo:
        resolved_repo = config.azure.repository_id

    fetcher = AzurePRFetcher(repository=resolved_repo, pr_url=pr_url)
    commenter = AzurePRCommenter(repository=resolved_repo, pr_url=pr_url) if post_comments else None

    rule_agent = RuleAgent()
    expert_agent = ExpertAgent()
    critic_agent = CriticAgent()

    # ✅ Repo-aware rules: generic + optional repo-specific
    rule_chunks = await load_rule_chunks(resolved_repo)
    prepared_chunks = prepare_chunks_for_store(rule_chunks)

    retriever = RuleRetriever()
    await retriever.build_index_if_needed(prepared_chunks)

    file_changes = await fetcher.fetch_file_changes(resolved_pr_id)
    valid_paths = {change.path for change in file_changes}

    all_added_lines: List[AddedLine] = []
    for change in file_changes:
        diff_text = build_diff_for_file(change.path, change.base_content, change.target_content)
        added = parse_unified_diff(diff_text, change.path)
        all_added_lines.extend(added)

    line_lookup: Dict[Any, str] = {}
    for line in all_added_lines:
        line_lookup[(line.file_path, line.line_number)] = line.content

    max_diff_chars = config.max_diff_chars
    chunks = chunk_added_lines(all_added_lines, max_chars=max_diff_chars)

    rule_results: List[Dict[str, Any]] = []
    expert_results: List[Dict[str, Any]] = []
    for chunk in chunks:
        retrieved_rules = await retriever.retrieve(chunk, top_k=config.max_rule_chunks)
        rule_result = await rule_agent.review(chunk, retrieved_rules)
        expert_result = await expert_agent.review(chunk)
        rule_results.append(rule_result)
        expert_results.append(expert_result)

    merged_rule = {
        "rule_violations": [],
        "compliance_score": 0,
    }
    for result in rule_results:
        merged_rule["rule_violations"].extend(result.get("rule_violations", []))

    merged_expert: Dict[str, Any] = {
        "bugs": [],
        "performance_issues": [],
        "security_issues": [],
        "scalability_issues": [],
        "refactor_suggestions": [],
        "test_cases_to_add": [],
        "architectural_concerns": [],
        "scores": {
            "performance": 0,
            "scalability": 0,
            "security": 0,
            "maintainability": 0,
            "readability": 0,
            "bug_risk": 0,
        },
    }

    for result in expert_results:
        for key in [
            "bugs",
            "performance_issues",
            "security_issues",
            "scalability_issues",
            "refactor_suggestions",
            "test_cases_to_add",
            "architectural_concerns",
        ]:
            merged_expert[key].extend(result.get(key, []))

        scores = result.get("scores", {})
        for score_key in merged_expert["scores"].keys():
            merged_expert["scores"][score_key] += float(scores.get(score_key, 0.0))

    if expert_results:
        count = float(len(expert_results))
        for score_key in merged_expert["scores"].keys():
            merged_expert["scores"][score_key] /= count

    scores = compute_overall_scores(merged_rule, merged_expert)

    combined: Dict[str, Any] = {
        "pull_request_id": resolved_pr_id,
        "repository": resolved_repo,
        "rule_result": merged_rule,
        "expert_result": merged_expert,
        "scores": scores,
    }

    refined = await critic_agent.refine(combined)

    refined_rule_result = refined.get("rule_result", merged_rule)
    refined_rule_result["rule_violations"] = postprocess_rule_violations(
        refined_rule_result.get("rule_violations", []),
        line_lookup,
    )

    refined_expert_result = refined.get("expert_result", merged_expert)
    for key in [
        "bugs",
        "performance_issues",
        "security_issues",
        "scalability_issues",
        "refactor_suggestions",
        "test_cases_to_add",
        "architectural_concerns",
    ]:
        refined_expert_result[key] = postprocess_rule_violations(
            refined_expert_result.get(key, []),
            line_lookup,
        )

    if post_comments and commenter is not None:
        summary = (
            f"Repo: {resolved_repo}\n"
            f"Overall score: {scores['overall_score']:.1f}/10\n"
            f"Performance: {scores['performance']:.1f}, Scalability: {scores['scalability']:.1f}, "
            f"Security: {scores['security']:.1f}, Maintainability: {scores['maintainability']:.1f}, "
            f"Readability: {scores['readability']:.1f}, Bug risk: {scores['bug_risk']:.1f}, "
            f"Rule compliance: {scores['rule_compliance']:.1f}"
        )
        await commenter.post_summary_comment(resolved_pr_id, summary)

    rule_violations = refined.get("rule_result", {}).get("rule_violations", [])
    expert_findings = refined.get("expert_result", {})

    if post_comments and commenter is not None:
        for violation in rule_violations:
            file_path = violation.get("file")
            if not file_path or file_path not in valid_paths:
                continue
            line_number = int(violation.get("line_number", 1))
            if line_number < 1:
                line_number = 1
            description = violation.get("description", "")
            fixed = violation.get("fixed_code_example", "")
            if not description and not fixed:
                continue
            content = f"Rule violation: {description}\n\nSuggested fix:\n{fixed}"
            await commenter.post_inline_comment(resolved_pr_id, file_path, line_number, content)

        for key in [
            "bugs",
            "performance_issues",
            "security_issues",
            "scalability_issues",
            "refactor_suggestions",
            "test_cases_to_add",
            "architectural_concerns",
        ]:
            for issue in expert_findings.get(key, []):
                file_path = issue.get("file")
                if not file_path or file_path not in valid_paths:
                    continue
                line_number = int(issue.get("line_number", 1))
                if line_number < 1:
                    line_number = 1
                description = issue.get("description", "")
                suggested = issue.get("suggested_fix", "")
                if not description and not suggested:
                    continue
                content = f"{key}: {description}\n\nSuggested fix:\n{suggested}"
                await commenter.post_inline_comment(resolved_pr_id, file_path, line_number, content)

    extra_prompt_response: Optional[str] = None
    if extra_prompt:
        client = AsyncOpenAI(api_key=config.openai.api_key)
        extra_payload = {
            "extra_prompt": extra_prompt,
            "review": {
                "repository": resolved_repo,
                "pull_request_id": resolved_pr_id,
                "rule_result": refined_rule_result,
                "expert_result": refined_expert_result,
                "scores": refined.get("scores", scores),
            },
        }
        extra_response = await client.chat.completions.create(
            model=config.openai.expert_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior reviewer. Given the review JSON and an extra user question, "
                        "provide a concise, structured answer focused on that question."
                    ),
                },
                {"role": "user", "content": json.dumps(extra_payload)},
            ],
        )
        extra_prompt_response = extra_response.choices[0].message.content or ""

    return {
        "pull_request_id": resolved_pr_id,
        "repository": resolved_repo,
        "rule_result": refined_rule_result,
        "expert_result": refined_expert_result,
        "scores": refined.get("scores", scores),
        "extra_prompt_response": extra_prompt_response,
    }