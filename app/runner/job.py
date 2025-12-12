import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.domain.models import AiDevTask, Job, JobState, Task
from app.runner.repo import clone_repo
from app.runner.sandbox import temp_sandbox
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
SANDBOX_BASE = Path("/Users/maxencehabar/Documents/PullSmith/.tmp")


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
        repo_url = task.repo_url if isinstance(task, Task) else task.repo
        branch = task.branch if isinstance(task, Task) else task.base_branch
        description = task.description or getattr(task, "title", "")
        instructions = _extract_instructions(description)
        print("instructions", instructions)
        logger.info("Starting job with repo %s branch %s", repo_url, branch)
        if isinstance(task, AiDevTask) and settings.trello_board_id:
            try:
                set_status_label(task.task_id, "WORKING", settings.trello_board_id)
            except Exception:
                logger.warning("Could not set Trello status to WORKING for %s", getattr(task, "task_id", ""))
        with temp_sandbox(base=SANDBOX_BASE) as sandbox:
            repo_path = clone_repo(repo_url, branch, sandbox)
            logger.info("Cloned repo to %s", repo_path)
            codex_result: CodexResult = run_codex_plan(repo_path, instructions)
            run_tests(repo_path)
            ensure_git_config(repo_path)
            raw_id = task.task_id if isinstance(task, AiDevTask) else getattr(task, "reference", "codex")
            branch_suggestion, commit_msg = propose_branch_and_commit(
                "",
                instructions,
            )
            branch_name = normalize_branch_name(branch_suggestion)[:50] or normalize_branch_name(f"feat/{sanitize_branch_name(raw_id)}")[:50]
            if branch_exists_remote(repo_path, branch_name):
                suffix_source = task.task_id if isinstance(task, AiDevTask) else getattr(task, "reference", "update")
                suffix = sanitize_branch_name(suffix_source)
                prefix, body = branch_name.split("/", 1)
                body = f"{body}-{suffix}" if suffix else body
                branch_name = normalize_branch_name(f"{prefix}/{body}")[:60]
            create_branch(repo_path, branch_name, base=branch)
            if not commit_all(repo_path, commit_msg):
                logger.info("No changes to commit for %s", raw_id)
                return
            if not settings.github_pat:
                logger.error("GITHUB_PAT not set; cannot push or open PR")
                return
            push_branch(repo_path, branch_name, token=settings.github_pat)
            pr_title = getattr(task, "title", None) or getattr(task, "pr_title", None) or f"Codex update {raw_id}"
            pr_body = instructions or getattr(task, "pr_body", "") or description
            pr_url = create_pull_request(repo_url, branch_name, branch, pr_title, pr_body, token=settings.github_pat)
            logger.info("PR created: %s", pr_url)
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
                add_comment(task.task_id, f"PR created: {pr_url}")
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
    return success
