import logging
import time

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _vercel_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _get_project_id(project_name: str, team_id: str, token: str) -> str:
    url = f"https://api.vercel.com/v9/projects/{project_name}"
    params = {"teamId": team_id} if team_id else {}
    resp = httpx.get(url, headers=_vercel_headers(token), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("id", "")


def _list_deployments(project_id: str, branch: str, team_id: str, token: str) -> list[dict]:
    url = "https://api.vercel.com/v6/deployments"
    params = {
        "projectId": project_id,
        "gitBranch": branch,
        "limit": 10,
    }
    if team_id:
        params["teamId"] = team_id
    resp = httpx.get(url, headers=_vercel_headers(token), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("deployments", [])


def _match_commit(deployment: dict, commit_sha: str) -> bool:
    meta = deployment.get("meta") or {}
    for key in ("githubCommitSha", "gitCommitSha", "commitSha"):
        if meta.get(key) == commit_sha:
            return True
    return False


def get_latest_deployment_url(
    project_name: str,
    branch: str,
    commit_sha: str | None = None,
    retries: int = 20,
    delay_seconds: int = 6,
) -> str:
    settings = get_settings()
    if not settings.vercel_token:
        logger.warning("VERCEL_TOKEN not set; skipping Vercel lookup")
        return ""
    project_id = _get_project_id(project_name, settings.vercel_team_id, settings.vercel_token)
    if not project_id:
        logger.warning("Could not resolve Vercel project id for %s", project_name)
        return ""
    for attempt in range(1, retries + 1):
        deployments = _list_deployments(project_id, branch, settings.vercel_team_id, settings.vercel_token)
        if commit_sha:
            target = next((d for d in deployments if _match_commit(d, commit_sha)), None)
            if target:
                state = target.get("state", "")
                if state == "READY":
                    url = target.get("url", "")
                    if not url:
                        return ""
                    if not url.startswith("https://"):
                        return f"https://{url}"
                    return url
                logger.info(
                    "Deployment for %s (%s) is %s, retry %s/%s",
                    project_name,
                    branch,
                    state or "unknown",
                    attempt,
                    retries,
                )
            else:
                logger.info(
                    "No deployment yet for %s (%s, commit %s), retry %s/%s",
                    project_name,
                    branch,
                    commit_sha[:7],
                    attempt,
                    retries,
                )
        else:
            if deployments:
                url = deployments[0].get("url", "")
                if not url:
                    return ""
                if not url.startswith("https://"):
                    return f"https://{url}"
                return url
            logger.info("No deployments yet for %s (%s), retry %s/%s", project_name, branch, attempt, retries)
        time.sleep(delay_seconds)
    return ""
