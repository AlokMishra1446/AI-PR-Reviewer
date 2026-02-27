from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..azure.pr_commenter import AzurePRCommenter
from ..azure.pr_fetcher import AzurePRFetcher
from ..orchestrator.pipeline import review_pull_request
from ..utils.logging import configure_logging


class ReviewRequest(BaseModel):
    pull_request_id: Optional[int] = None
    pr_url: Optional[str] = None
    extra_prompt: Optional[str] = None
    repository: Optional[str] = None


class CommentRequest(BaseModel):
    pull_request_id: Optional[int] = None
    pr_url: Optional[str] = None
    repository: Optional[str] = None
    file: str
    line_number: int
    content: str


configure_logging()
app = FastAPI(title="AI PR Reviewer", version="1.0.0")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/review/pr")
async def review_pr(request: ReviewRequest) -> Dict[str, Any]:
    try:
        result = await review_pull_request(
            pull_request_id=request.pull_request_id,
            pr_url=request.pr_url,
            extra_prompt=request.extra_prompt,
            post_comments=False,
            repository=request.repository,
        )
        return result
    except ValueError as exc:
        message = str(exc)
        if "Pull request" in message and "not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/comment/pr")
async def comment_pr(request: CommentRequest) -> Dict[str, Any]:
    try:
        line_number = max(1, request.line_number)
        file_path = request.file

        # Try to canonicalize path using fetcher
        try:
            fetcher = AzurePRFetcher(repository=request.repository, pr_url=request.pr_url)
            file_changes = await fetcher.fetch_file_changes(request.pull_request_id)
        except Exception:
            file_changes = []

        if file_changes:
            paths = [change.path for change in file_changes]
            canonical: Optional[str] = None
            if file_path in paths:
                canonical = file_path
            else:
                for path in paths:
                    if path.endswith(file_path) or path.endswith("/" + file_path):
                        canonical = path
                        break
            if canonical:
                file_path = canonical

        commenter = AzurePRCommenter(repository=request.repository, pr_url=request.pr_url)
        result = await commenter.post_inline_comment(
            request.pull_request_id,
            file_path,
            line_number,
            request.content,
        )
        if isinstance(result, dict) and "error" in result:
            status = int(result.get("status_code", 400) or 400)
            raise HTTPException(status_code=status, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc