import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParsedPRUrl:
    organization: str
    project: str
    repository: str
    pull_request_id: int


def parse_azure_pr_url(pr_url: str) -> ParsedPRUrl:
    """
    Supports both:
    1) https://{org}.visualstudio.com/{project}/_git/{repo}/pullrequest/{id}
    2) https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
    """

    patterns = [
        (
            r"^https://(?P<org>[^/.]+)\.visualstudio\.com/"
            r"(?P<project>[^/]+)/_git/"
            r"(?P<repo>[^/]+)/pullrequest/"
            r"(?P<pr_id>\d+)"
        ),
        (
            r"^https://dev\.azure\.com/(?P<org>[^/]+)/"
            r"(?P<project>[^/]+)/_git/"
            r"(?P<repo>[^/]+)/pullrequest/"
            r"(?P<pr_id>\d+)"
        ),
    ]

    for pattern in patterns:
        m = re.match(pattern, pr_url.strip())
        if m:
            return ParsedPRUrl(
                organization=m.group("org"),
                project=m.group("project"),
                repository=m.group("repo"),
                pull_request_id=int(m.group("pr_id")),
            )

    raise ValueError("Invalid Azure DevOps PR URL format")