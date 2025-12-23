import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RepoInfo:
    owner: str
    name: str
    clone_url: str


def _run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Command %s failed: %s", " ".join(cmd), result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result.stdout.strip()


def ensure_git_config(
    repo_path: Path,
    user: str = "youdyApprentis",
    email: str = "youdyApprentis@users.noreply.github.com",
) -> None:
    _run(["git", "config", "user.name", user], cwd=repo_path)
    _run(["git", "config", "user.email", email], cwd=repo_path)


def create_branch(repo_path: Path, branch: str, base: Optional[str] = None) -> None:
    if base:
        _run(["git", "checkout", base], cwd=repo_path)
    logger.info("Checking out branch %s", branch)
    _run(["git", "checkout", "-B", branch], cwd=repo_path)


def commit_all(repo_path: Path, message: str) -> bool:
    status = _run(["git", "status", "--porcelain"], cwd=repo_path)
    if not status:
        logger.info("No changes to commit")
        return False
    _run(["git", "add", "-A"], cwd=repo_path)
    _run(["git", "commit", "-m", message], cwd=repo_path)
    return True


def branch_exists_remote(repo_path: Path, branch: str) -> bool:
    try:
        out = _run(["git", "ls-remote", "--heads", "origin", branch], cwd=repo_path)
        return bool(out)
    except subprocess.CalledProcessError:
        return False


def push_branch(repo_path: Path, branch: str, token: Optional[str] = None) -> None:
    remote_url = _run(["git", "config", "--get", "remote.origin.url"], cwd=repo_path)
    if token and remote_url.startswith("https://github.com/"):
        # Inject token for push
        authed = remote_url.replace("https://github.com/", f"https://{token}@github.com/")
        _run(["git", "remote", "set-url", "origin", authed], cwd=repo_path)
    logger.info("Pushing branch %s", branch)
    _run(["git", "push", "-u", "origin", branch], cwd=repo_path)
    # restore remote url if it was changed
    if token and remote_url.startswith("https://github.com/"):
        _run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_path)


def parse_repo_info(url: str) -> RepoInfo:
    cleaned = url
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    if cleaned.startswith("https://github.com/"):
        parts = cleaned.split("https://github.com/", 1)[1].split("/")
    elif cleaned.startswith("git@github.com:"):
        parts = cleaned.split("git@github.com:", 1)[1].split("/")
    else:
        raise ValueError(f"Unsupported repo url: {url}")
    owner, name = parts[0], parts[1]
    return RepoInfo(owner=owner, name=name, clone_url=url)


def create_pull_request(
    repo_url: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    token: str,
) -> str:
    repo = parse_repo_info(repo_url)
    api_url = f"https://api.github.com/repos/{repo.owner}/{repo.name}/pulls"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    payload = {"title": title, "head": head_branch, "base": base_branch, "body": body}
    logger.info("Creating pull request %s -> %s/%s", head_branch, repo.owner, repo.name)
    resp = httpx.post(api_url, headers=headers, json=payload, timeout=10)
    if resp.status_code >= 300:
        logger.error("Failed to create PR: %s", resp.text)
        raise RuntimeError(f"Failed to create PR: {resp.status_code}")
    pr_url = resp.json().get("html_url", "")
    logger.info("Created PR: %s", pr_url)
    return pr_url
