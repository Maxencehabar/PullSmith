import logging
from typing import Any

from app.domain.models import Task

logger = logging.getLogger(__name__)


def parse_github_pr(payload: dict[str, Any]) -> Task:
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    repo_url = repo.get("clone_url") or repo.get("html_url", "")
    description = pr.get("body") or pr.get("title") or "GitHub PR"
    return Task(
        source="github",
        reference=str(pr.get("id", "")),
        repo_url=repo_url,
        branch=pr.get("head", {}).get("ref", "main"),
        description=description,
        pr_title=pr.get("title"),
        pr_body=description,
    )
