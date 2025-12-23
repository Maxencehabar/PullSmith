import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _run_git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def _run_git_optional(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def _auth_url(url: str) -> tuple[str, bool]:
    token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    if token and url.startswith("https://github.com/"):
        parts = url.split("https://github.com/", 1)[1]
        return f"https://{token}@github.com/{parts}", True
    return url, False


def _repo_dir_name(url: str) -> str:
    cleaned = url.rstrip("/").rsplit("/", 2)
    slug = "-".join(cleaned[-2:]) if len(cleaned) >= 2 else cleaned[-1]
    safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_").strip("-_") or "repo"
    return safe_slug


def _remote_branch_exists(repo_dir: Path, branch: str) -> bool:
    result = _run_git_optional(["git", "ls-remote", "--heads", "origin", branch], cwd=repo_dir)
    return result.returncode == 0 and bool(result.stdout.strip())


def _default_branch(repo_dir: Path) -> str:
    result = _run_git_optional(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_dir
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("/")[-1]
    return "main"


def prepare_repo(url: str, branch: str, cache_base: Path) -> tuple[Path, str]:
    auth_url, authed = _auth_url(url)
    repo_dir = cache_base / _repo_dir_name(url)
    cache_base.mkdir(parents=True, exist_ok=True)

    if repo_dir.exists():
        logger.info("Updating repo in %s", repo_dir)
        _run_git(["git", "remote", "set-url", "origin", auth_url], cwd=repo_dir)
        _run_git(["git", "fetch", "origin"], cwd=repo_dir)
        target_branch = branch if _remote_branch_exists(repo_dir, branch) else _default_branch(repo_dir)
        if target_branch != branch:
            logger.info("Branch %s not found; using %s", branch, target_branch)
        _run_git(["git", "checkout", "-B", target_branch, f"origin/{target_branch}"], cwd=repo_dir)
        _run_git(["git", "reset", "--hard", f"origin/{target_branch}"], cwd=repo_dir)
        _run_git(["git", "clean", "-fdx"], cwd=repo_dir)
    else:
        logger.info("Cloning repo into %s", repo_dir)
        try:
            _run_git(["git", "clone", "--branch", branch, auth_url, str(repo_dir)], cwd=cache_base)
            target_branch = branch
        except subprocess.CalledProcessError:
            logger.info("Branch %s not found; cloning default branch", branch)
            _run_git(["git", "clone", auth_url, str(repo_dir)], cwd=cache_base)
            target_branch = branch if _remote_branch_exists(repo_dir, branch) else _default_branch(repo_dir)
            if target_branch != branch:
                logger.info("Using default branch %s", target_branch)
            _run_git(["git", "checkout", "-B", target_branch, f"origin/{target_branch}"], cwd=repo_dir)

    if authed:
        _run_git(["git", "remote", "set-url", "origin", url], cwd=repo_dir)

    return repo_dir, target_branch
