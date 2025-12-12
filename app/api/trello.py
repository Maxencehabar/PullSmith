import logging
from fastapi import APIRouter, Header, HTTPException

from app.services.orchestrator import enqueue_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/")
async def trello_webhook(payload: dict, x_trello_webhook: str = Header(None)) -> dict:
    if not x_trello_webhook:
        raise HTTPException(status_code=401)

    action = payload.get("action", {})
    if action.get("type") != "updateCard":
        logger.info("Ignoring Trello webhook: action type %s", action.get("type"))
        return {"ignored": True}

    list_after = action.get("data", {}).get("listAfter", {}) or {}
    if list_after.get("name") != "AI Ready":
        logger.info("Ignoring Trello webhook: listAfter %s", list_after.get("name"))
        return {"ignored": True}

    task = await enqueue_task(payload)
    if task is None:
        logger.warning("Ignoring Trello webhook: missing repo attachment and no REPO_URL set")
        return {"ignored": True, "reason": "missing repo attachment on card"}
    return {"status": "accepted"}


@router.get("/")
async def trello_webhook_verification() -> dict:
    # Trello calls GET/HEAD during webhook creation to verify the endpoint.
    return {"status": "ok"}


@router.head("/")
async def trello_webhook_head() -> None:
    # Respond 200 for Trello HEAD verification.
    return None
