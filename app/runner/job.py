import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.domain.models import AiDevTask, Job, JobState, Task
from app.runner.repo import prepare_repo
from app.runner.verifier import run_tests
from app.services.codex_agent import CodexResult, run_codex_plan
from app.services.git_service import (
    branch_exists_remote,
    commit_all,
    create_branch,
    create_pull_request,
    ensure_git_config,
    push_branch,
)
from app.services.trello_service import add_comment, get_list_id_by_name, move_card_to_list, set_status_label
from app.services.llm import propose_branch_and_commit
from app.domain.policies import normalize_branch_name, sanitize_branch_name

logger = logging.getLogger(__name__)
def _resolve_repo_urls(task: Task | AiDevTask, settings) -> list[str]:
    if isinstance(task, Task):
        return [str(task.repo_url)]
    if task.repos:
        return task.repos
    return settings.repo_urls


def _set_error_status(task: Task | AiDevTask, settings) -> None:
    if isinstance(task, AiDevTask) and settings.trello_board_id:
        try:
            set_status_label(task.task_id, "ERROR", settings.trello_board_id)
        except Exception:
            logger.warning("Could not set Trello status to ERROR for %s", getattr(task, "task_id", ""))


def _deploy_functions(repo_path: Path) -> None:
    logger.info("Deploying youdy-functions to pre-prod")
    subprocess.run(
        ["npm", "run", "deploy-test", "--", "--only", "functions"],
        cwd=repo_path,
        check=True,
    )


def _extract_instructions(description: str) -> str:
    """Return text after 'Instructions :' (any spacing/newline), or the whole description if absent."""
    if not description:
        return ""
    match = re.search(r"Instructions\s*:\s*(.*)", description, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return description.strip()


async def run_job(job: Any) -> bool:
    job_obj = job if isinstance(job, Job) else None
    task: Task | AiDevTask = job.task if job_obj else job
    if job_obj:
        job_obj.state = JobState.running
    success = False
    try:
        settings = get_settings()
        repo_urls = _resolve_repo_urls(task, settings)
        if not repo_urls:
            logger.error("No repositories configured for task")
            _set_error_status(task, settings)
            return False
        branch = task.branch if isinstance(task, Task) else task.base_branch
        description = task.description or getattr(task, "title", "")
        instructions = _extract_instructions(description)
        print("instructions", instructions)
        logger.info("Starting job with %s repos on branch %s", len(repo_urls), branch)
        if isinstance(task, AiDevTask) and settings.trello_board_id:
            try:
                set_status_label(task.task_id, "WORKING", settings.trello_board_id)
            except Exception:
                logger.warning("Could not set Trello status to WORKING for %s", getattr(task, "task_id", ""))
        repo_base = Path(settings.repo_root)
        prepared = [prepare_repo(url, branch, repo_base) for url in repo_urls]
        repo_paths = [repo_path for repo_path, _ in prepared]
        repo_branches = [target_branch for _, target_branch in prepared]
        codex_root = repo_paths[0] if len(repo_paths) == 1 else repo_base
        logger.info("Prepared repos under %s", repo_base)
        codex_result: CodexResult = run_codex_plan(codex_root, instructions)
        for repo_path in repo_paths:
            run_tests(repo_path)
            ensure_git_config(repo_path)
        raw_id = task.task_id if isinstance(task, AiDevTask) else getattr(task, "reference", "codex")
        branch_suggestion, commit_msg = propose_branch_and_commit(
            "",
            instructions,
        )
        if not settings.github_pat:
            logger.error("GITHUB_PAT not set; cannot push or open PR")
            _set_error_status(task, settings)
            return
        pr_title = getattr(task, "title", None) or getattr(task, "pr_title", None) or f"Codex update {raw_id}"
        pr_body = instructions or getattr(task, "pr_body", "") or description
        base_branch_name = normalize_branch_name(branch_suggestion)[:50] or normalize_branch_name(
            f"feat/{sanitize_branch_name(raw_id)}"
        )[:50]
        pr_links: list[tuple[str, str]] = []
        for repo_url, repo_path, repo_branch in zip(repo_urls, repo_paths, repo_branches, strict=False):
            branch_name = base_branch_name
            if branch_exists_remote(repo_path, branch_name):
                suffix_source = task.task_id if isinstance(task, AiDevTask) else getattr(task, "reference", "update")
                suffix = sanitize_branch_name(suffix_source)
                prefix, body = branch_name.split("/", 1)
                body = f"{body}-{suffix}" if suffix else body
                branch_name = normalize_branch_name(f"{prefix}/{body}")[:60]
            create_branch(repo_path, branch_name, base=repo_branch)
            if not commit_all(repo_path, commit_msg):
                logger.info("No changes to commit for %s in %s", raw_id, repo_url)
                continue
            push_branch(repo_path, branch_name, token=settings.github_pat)
            pr_url = create_pull_request(repo_url, branch_name, repo_branch, pr_title, pr_body, token=settings.github_pat)
            logger.info("PR created: %s", pr_url)
            repo_name = repo_url.rstrip("/").split("/")[-1]
            pr_links.append((repo_name, pr_url))
            if repo_name == "youdy-functions":
                _deploy_functions(repo_path)
        if not pr_links:
            logger.info("No changes to commit for %s", raw_id)
            return
        if isinstance(task, AiDevTask):
            board_id = settings.trello_board_id
            list_id = get_list_id_by_name(board_id, "In Review") if board_id else ""
            if list_id:
                move_card_to_list(task.task_id, list_id)
            try:
                if board_id:
                    set_status_label(task.task_id, "SUBMITTED", board_id)
            except Exception:
                logger.warning("Could not set Trello status to SUBMITTED for %s", task.task_id)
            comment_lines = [f"{repo_name}: {pr_url}" for repo_name, pr_url in pr_links]
            comment_body = "PRs created:\n" + "\n".join(comment_lines)
            add_comment(task.task_id, comment_body)
        success = True
        if job_obj:
            job_obj.state = JobState.succeeded if success else JobState.failed
            logger.info("Job %s %s", job_obj.id, "succeeded" if success else "failed")
    except Exception as exc:  # noqa: BLE001
        if job_obj:
            job_obj.state = JobState.failed
            job_obj.add_log(str(exc))
            logger.exception("Job %s failed: %s", job_obj.id, exc)
        else:
            logger.exception("Job failed: %s", exc)
        _set_error_status(task, settings)
    return success
