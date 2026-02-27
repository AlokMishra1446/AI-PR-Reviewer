import base64
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from ..utils.config import load_config
from .pr_url_parser import parse_azure_pr_url


@dataclass
class FileChange:
    path: str
    base_content: str
    target_content: str


class AzurePRFetcher:
    def __init__(
        self,
        repository: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> None:
        self.config = load_config()

        # Defaults from config
        self.organization = self.config.azure.organization
        self.project = self.config.azure.project
        self.repository = repository or self.config.azure.repository_id
        self.pull_request_id_from_url: Optional[int] = None

        # Override from PR URL if provided
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

    async def _get(self, client: httpx.AsyncClient, url: str, params: Optional[Dict[str, str]] = None) -> Dict:
        response = await client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    async def _get_pull_request(self, client: httpx.AsyncClient, pull_request_id: int) -> Dict:
        url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}"
        return await self._get(client, url, params={"api-version": "7.1"})

    async def _get_latest_iteration_id(self, client: httpx.AsyncClient, pull_request_id: int) -> int:
        url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/iterations"
        data = await self._get(client, url, params={"api-version": "7.1"})
        iterations = data.get("value", [])
        if not iterations:
            return 1
        return max(iteration.get("id", 1) for iteration in iterations)

    async def _get_iteration_changes(self, client: httpx.AsyncClient, pull_request_id: int, iteration_id: int) -> List[Dict]:
        url = f"{self.base_url}/_apis/git/repositories/{self.repository}/pullRequests/{pull_request_id}/iterations/{iteration_id}/changes"
        data = await self._get(client, url, params={"api-version": "7.1"})
        return data.get("changeEntries", [])

    async def _get_file_content_at_commit(self, client: httpx.AsyncClient, path: str, commit_id: str) -> str:
        url = f"{self.base_url}/_apis/git/repositories/{self.repository}/items"
        params = {
            "path": path,
            "versionType": "commit",
            "version": commit_id,
            "includeContent": "true",
            "api-version": "7.1",
        }
        try:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return ""
            raise
        return response.text

    async def fetch_file_changes(self, pull_request_id: Optional[int] = None) -> List[FileChange]:
        if pull_request_id is None:
            if self.pull_request_id_from_url is None:
                raise ValueError("Pull request ID must be provided (or provide pr_url).")
            pull_request_id = self.pull_request_id_from_url

        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            try:
                pr_data = await self._get_pull_request(client, pull_request_id)
            except httpx.HTTPStatusError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    raise ValueError(f"Pull request {pull_request_id} was not found in Azure DevOps") from exc
                raise

            source_commit_id = ((pr_data.get("lastMergeSourceCommit") or {}).get("commitId") or "")
            target_commit_id = ((pr_data.get("lastMergeTargetCommit") or {}).get("commitId") or "")

            iteration_id = await self._get_latest_iteration_id(client, pull_request_id)
            changes = await self._get_iteration_changes(client, pull_request_id, iteration_id)

            file_changes: List[FileChange] = []
            for entry in changes:
                item = entry.get("item") or {}
                original = entry.get("originalItem") or {}
                path = item.get("path") or original.get("path")
                if not path:
                    continue

                change_type = entry.get("changeType", "").lower()
                if change_type not in {"add", "edit", "rename"}:
                    continue

                target_content = await self._get_file_content_at_commit(client, path, source_commit_id) if source_commit_id else ""
                base_content = await self._get_file_content_at_commit(client, path, target_commit_id) if target_commit_id else ""

                file_changes.append(FileChange(path=path, base_content=base_content, target_content=target_content))

            return file_changes