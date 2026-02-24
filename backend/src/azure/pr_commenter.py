import base64
from typing import Any, Dict, List, Optional

import httpx

from ..utils.config import load_config


class AzurePRCommenter:
    def __init__(self, repository: Optional[str] = None) -> None:
        self.config = load_config()
        token = self.config.azure.pat_token
        basic = base64.b64encode(f":{token}".encode("utf-8")).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/json",
        }
        self.base_url = f"https://dev.azure.com/{self.config.azure.organization}/{self.config.azure.project}"
        self.repository = repository or self.config.azure.repository_id

    async def _post(self, client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await client.post(url, headers=self.headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return {
                "error": str(exc),
                "status_code": response.status_code,
            }
        return response.json()

    async def post_inline_comment(
        self,
        pull_request_id: int,
        file_path: str,
        line_number: int,
        content: str,
        parent_thread_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/threads?api-version=7.1"
            thread_context = {
                "filePath": file_path,
                "rightFileStart": {"line": line_number, "offset": 1},
                "rightFileEnd": {"line": line_number, "offset": 1},
            }
            payload: Dict[str, Any] = {
                "status": "active",
                "comments": [
                    {
                        "parentCommentId": 0,
                        "content": content,
                        "commentType": "text",
                    }
                ],
                "threadContext": thread_context,
            }
            if parent_thread_id is not None:
                payload["id"] = parent_thread_id
            return await self._post(client, url, payload)

    async def post_summary_comment(self, pull_request_id: int, content: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/threads?api-version=7.1"
            payload: Dict[str, Any] = {
                "status": "active",
                "comments": [
                    {
                        "parentCommentId": 0,
                        "content": content,
                        "commentType": "text",
                    }
                ],
            }
            return await self._post(client, url, payload)
