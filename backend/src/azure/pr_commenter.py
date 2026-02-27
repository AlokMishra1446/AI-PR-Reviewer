import base64
from typing import Any, Dict, Optional

import httpx

from ..utils.config import load_config
from .pr_url_parser import parse_azure_pr_url


class AzurePRCommenter:
    def __init__(
        self,
        repository: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> None:
        self.config = load_config()

        self.organization = self.config.azure.organization
        self.project = self.config.azure.project
        self.repository = repository or self.config.azure.repository_id
        self.pull_request_id_from_url: Optional[int] = None

        if pr_url:
            parsed = parse_azure_pr_url(pr_url)
            self.organization = parsed.organization
            self.project = parsed.project
            self.repository = parsed.repository
            self.pull_request_id_from_url = parsed.pull_request_id

        token = self.config.azure.pat_token
        basic = base64.b64encode(f":{token}".encode("utf-8")).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/json",
        }
        self.base_url = f"https://dev.azure.com/{self.organization}/{self.project}"

    async def _post(self, client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await client.post(url, headers=self.headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return {"error": str(exc), "status_code": response.status_code}
        return response.json()

    async def post_inline_comment(
        self,
        pull_request_id: Optional[int],
        file_path: str,
        line_number: int,
        content: str,
        parent_thread_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if pull_request_id is None:
            if self.pull_request_id_from_url is None:
                raise ValueError("Pull request ID must be provided (or provide pr_url).")
            pull_request_id = self.pull_request_id_from_url

        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/threads?api-version=7.1"
            thread_context = {
                "filePath": file_path,
                "rightFileStart": {"line": line_number, "offset": 1},
                "rightFileEnd": {"line": line_number, "offset": 1},
            }
            payload: Dict[str, Any] = {
                "status": "active",
                "comments": [{"parentCommentId": 0, "content": content, "commentType": "text"}],
                "threadContext": thread_context,
            }
            if parent_thread_id is not None:
                payload["id"] = parent_thread_id
            return await self._post(client, url, payload)

    async def post_summary_comment(self, pull_request_id: Optional[int], content: str) -> Dict[str, Any]:
        if pull_request_id is None:
            if self.pull_request_id_from_url is None:
                raise ValueError("Pull request ID must be provided (or provide pr_url).")
            pull_request_id = self.pull_request_id_from_url

        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/threads?api-version=7.1"
            payload: Dict[str, Any] = {
                "status": "active",
                "comments": [{"parentCommentId": 0, "content": content, "commentType": "text"}],
            }
            return await self._post(client, url, payload)