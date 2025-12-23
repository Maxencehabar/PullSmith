import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.domain.models import AiDevTask, Job, Task
from app.runner.job import run_job
from app.workers.worker import JobQueue
from app.services.trello_service import (
    get_list_id_by_name,
    has_status_label,
    set_status_label,
)

logger = logging.getLogger(__name__)
PROCESSED_FILE = Path(__file__).resolve().parents[2] / ".processed_cards"


def _find_url_in_text(text: str) -> str:
    if not text:
        print("description is empty")
        return ""
    candidates = re.findall(r"https?://[^\s\]\)]+", text)
    print("url candidates from description", candidates)
    if not candidates:
        print("no url candidates in description")
        return ""
    url = candidates[0].rstrip(".,)")
    print("chosen url from description", url)
    return url


def _fetch_card(card_id: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.trello_key or not settings.trello_token or not card_id:
        return {}
    try:
        resp = httpx.get(
            f"https://api.trello.com/1/cards/{card_id}",
            params={
                "key": settings.trello_key,
                "token": settings.trello_token,
                "attachments": "true",
                "fields": "desc",
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to fetch Trello card %s: %s", card_id, exc)
        return {}


def _extract_repo(card: dict[str, Any]) -> str:
    print("card", card)
    attachments = card.get("attachments") or []
    print("attachments", attachments)
    for attachment in attachments:
        url = attachment.get("url")
        if url:
            print("url", url)
            return url

    url_in_desc = _find_url_in_text(card.get("desc", ""))
    print("url_in_desc", url_in_desc)
    if url_in_desc:
        return url_in_desc

    full_card = _fetch_card(card.get("id", ""))
    if full_card:
        attachments = full_card.get("attachments") or []
        print("attachments from fetch", attachments)
        for attachment in attachments:
            url = attachment.get("url")
            if url:
                print("url from fetched attachment", url)
                return url
        url_in_desc = _find_url_in_text(full_card.get("desc", ""))
        if url_in_desc:
            return url_in_desc

    return ""


def _extract_repos(card: dict[str, Any]) -> list[str]:
    settings = get_settings()
    if settings.repo_urls:
        return settings.repo_urls
    url = _extract_repo(card)
    return [url] if url else []


def _extract_checklist(card: dict[str, Any]) -> list[str]:
    checklists = card.get("checklists") or []
    items: list[str] = []
    for checklist in checklists:
        for item in checklist.get("checkItems", []):
            name = item.get("name")
            if name:
                items.append(name)
    return items


def _load_processed() -> set[str]:
    if not PROCESSED_FILE.exists():
        return set()
    try:
        return set(line.strip() for line in PROCESSED_FILE.read_text().splitlines() if line.strip())
    except Exception:
        return set()


def _mark_processed(card_id: str) -> None:
    try:
        PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PROCESSED_FILE.open("a") as f:
            f.write(card_id + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to mark card %s as processed: %s", card_id, exc)


async def enqueue_task(payload: dict[str, Any]) -> AiDevTask:
    card = payload.get("action", {}).get("data", {}).get("card", {})
    full_card = _fetch_card(card.get("id", ""))
    if full_card:
        # Prefer fetched data for full description/attachments.
        card = {**card, **full_card}
    processed = _load_processed()
    if card.get("id") in processed:
        logger.info("Skipping card %s: already processed", card.get("id"))
        return None
    settings = get_settings()
    ai_ready_list_id = (
        get_list_id_by_name(settings.trello_board_id, "AI Ready") if settings.trello_board_id else ""
    )
    if ai_ready_list_id and card.get("idList") and card.get("idList") != ai_ready_list_id:
        logger.info("Skipping card %s: not in AI Ready", card.get("id", ""))
        return None
    if settings.trello_board_id and has_status_label(card.get("id", ""), "SUBMITTED", settings.trello_board_id):
        logger.info("Skipping card %s: already SUBMITTED", card.get("id", ""))
        return None
    if settings.trello_board_id and has_status_label(card.get("id", ""), "WORKING", settings.trello_board_id):
        logger.info("Skipping card %s: already WORKING", card.get("id", ""))
        return None
    repos = _extract_repos(card)
    task = AiDevTask(
        task_id=card.get("id", ""),
        title=card.get("name", ""),
        description=card.get("desc", ""),
        repos=repos,
        base_branch="main",
        acceptance_criteria=_extract_checklist(card),
    )
    print("task", task)
    if not task.repos:
        logger.warning("Skipping card %s: no repos configured or found", task.task_id)
        return None
    success = await run_job(task)
    if success:
        _mark_processed(task.task_id)
    return task


class Orchestrator:
    def __init__(self, queue: JobQueue | None = None) -> None:
        self.queue = queue or JobQueue()
        self._worker_started = False

    async def start_worker(self) -> None:
        if self._worker_started:
            return
        self._worker_started = True
        asyncio.create_task(self.queue.work(run_job))
        logger.info("Runner worker started")

    async def submit_task(self, task: Task) -> Job:
        job = Job(id=str(uuid.uuid4()), task=task)
        await self.queue.enqueue(job)
        logger.info("Submitted task %s for repo %s", job.id, task.repo_url)
        return job
