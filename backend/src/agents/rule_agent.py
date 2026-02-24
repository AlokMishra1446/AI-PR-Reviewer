import json
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..embeddings.retriever import RetrievedRule
from ..utils.config import load_config


class RuleAgent:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = AsyncOpenAI(api_key=self.config.openai.api_key)

    def _safe_parse(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"rule_violations": [], "compliance_score": 10}

    async def review(self, diff_chunk: str, rules: List[RetrievedRule]) -> Dict[str, Any]:
        system_prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "rule_prompt.txt"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        rules_payload = [
            {"text": r.text, "metadata": r.metadata, "score": r.score} for r in rules
        ]
        user_content = {
            "diff_chunk": diff_chunk,
            "retrieved_rules": rules_payload,
        }
        response = await self.client.chat.completions.create(
            model=self.config.openai.rule_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_content)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._safe_parse(content)
