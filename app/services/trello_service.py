import logging
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings
from app.domain.models import Task

logger = logging.getLogger(__name__)
STATUS_NAMES = {"PENDING", "WORKING", "SUBMITTED", "ERROR"}


def parse_trello_card(payload: dict[str, Any]) -> Task:
    card = payload.get("action", {}).get("data", {}).get("card", {})
    attachments = payload.get("action", {}).get("data", {}).get("attachments", [])
    repo_url = next((a.get("url") for a in attachments if a.get("url")), "")
    description = card.get("desc") or card.get("name") or "Trello card"
    return Task(
        source="trello",
        reference=card.get("id", ""),
        repo_url=repo_url,
        description=description,
    )


@lru_cache(maxsize=1)
def _trello_auth() -> dict[str, str]:
    settings = get_settings()
    if not (settings.trello_key and settings.trello_token):
        raise RuntimeError("Trello key/token not configured")
    return {"key": settings.trello_key, "token": settings.trello_token}


def _trello_client() -> httpx.Client:
    return httpx.Client(timeout=10)


def get_list_id_by_name(board_id: str, list_name: str) -> str:
    auth = _trello_auth()
    with _trello_client() as client:
        resp = client.get(
            f"https://api.trello.com/1/boards/{board_id}/lists",
            params=auth,
        )
        resp.raise_for_status()
        for lst in resp.json():
            if lst.get("name") == list_name:
                return lst.get("id", "")
    return ""


def move_card_to_list(card_id: str, list_id: str) -> None:
    if not list_id:
        return
    auth = _trello_auth()
    with _trello_client() as client:
        resp = client.put(
            f"https://api.trello.com/1/cards/{card_id}",
            params={**auth, "idList": list_id},
        )
        resp.raise_for_status()
    logger.info("Moved card %s to list %s", card_id, list_id)


def add_comment(card_id: str, text: str) -> None:
    auth = _trello_auth()
    with _trello_client() as client:
        resp = client.post(
            f"https://api.trello.com/1/cards/{card_id}/actions/comments",
            params={**auth, "text": text},
        )
        resp.raise_for_status()
    logger.info("Added comment to card %s", card_id)


def _get_labels(board_id: str) -> dict[str, str]:
    auth = _trello_auth()
    with _trello_client() as client:
        resp = client.get(
            f"https://api.trello.com/1/boards/{board_id}/labels",
            params={**auth, "limit": 1000},
        )
        resp.raise_for_status()
        labels = resp.json()
        return {lbl.get("name", "").upper(): lbl.get("id", "") for lbl in labels}


def _get_card_labels(card_id: str) -> list[str]:
    auth = _trello_auth()
    with _trello_client() as client:
        resp = client.get(
            f"https://api.trello.com/1/cards/{card_id}",
            params={**auth, "fields": "idLabels"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("idLabels", [])


def set_status_label(card_id: str, status: str, board_id: str) -> None:
    if not card_id or not board_id or not status:
        return
    status_upper = status.upper()
    if status_upper not in STATUS_NAMES:
        logger.warning("Unknown status %s for card %s", status, card_id)
        return
    try:
        label_map = _get_labels(board_id)
        target_label = label_map.get(status_upper)
        if not target_label:
            logger.warning("Status label %s not found on board %s", status_upper, board_id)
            return
        current_labels = set(_get_card_labels(card_id))
        status_label_ids = {lbl_id for name, lbl_id in label_map.items() if name in STATUS_NAMES}
        to_remove = [lbl for lbl in current_labels if lbl in status_label_ids and lbl != target_label]
        auth = _trello_auth()
        with _trello_client() as client:
            for lbl in to_remove:
                client.delete(f"https://api.trello.com/1/cards/{card_id}/idLabels/{lbl}", params=auth)
            if target_label not in current_labels:
                client.post(
                    f"https://api.trello.com/1/cards/{card_id}/idLabels",
                    params={**auth, "value": target_label},
                )
        logger.info("Set status %s for card %s", status_upper, card_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to set status %s for card %s: %s", status, card_id, exc)


def has_status_label(card_id: str, status: str, board_id: str) -> bool:
    if not card_id or not board_id or not status:
        return False
    status_upper = status.upper()
    if status_upper not in STATUS_NAMES:
        return False
    try:
        label_map = _get_labels(board_id)
        target_label = label_map.get(status_upper)
        if not target_label:
            return False
        current_labels = set(_get_card_labels(card_id))
        return target_label in current_labels
    except Exception:
        return False
