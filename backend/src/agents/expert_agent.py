import json
from pathlib import Path
from typing import Any, Dict

from openai import AsyncOpenAI

from ..utils.config import load_config


class ExpertAgent:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = AsyncOpenAI(api_key=self.config.openai.api_key)

    def _safe_parse(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "bugs": [],
                "performance_issues": [],
                "security_issues": [],
                "scalability_issues": [],
                "refactor_suggestions": [],
                "test_cases_to_add": [],
                "architectural_concerns": [],
                "scores": {
                    "performance": 5,
                    "scalability": 5,
                    "security": 5,
                    "maintainability": 5,
                    "readability": 5,
                    "bug_risk": 5,
                },
            }

    async def review(self, diff_chunk: str) -> Dict[str, Any]:
        system_prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "expert_prompt.txt"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        response = await self.client.chat.completions.create(
            model=self.config.openai.expert_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": diff_chunk},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._safe_parse(content)
