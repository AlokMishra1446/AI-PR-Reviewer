import json
from pathlib import Path
from typing import Any, Dict

from openai import AsyncOpenAI

from ..utils.config import load_config


class CriticAgent:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = AsyncOpenAI(api_key=self.config.openai.api_key)

    def _safe_parse(self, content: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return fallback

    async def refine(self, combined_result: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "critic_prompt.txt"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        response = await self.client.chat.completions.create(
            model=self.config.openai.critic_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(combined_result)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._safe_parse(content, combined_result)
