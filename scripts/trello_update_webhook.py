#!/usr/bin/env python3
import os
import sys

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - runtime guard
    requests = None


def _load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                os.environ.setdefault(key, value)
    except OSError:
        return


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing {name} in environment.", file=sys.stderr)
        raise SystemExit(1)
    return value


def _parse_args() -> str:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/trello_update_webhook.py <callback-url>", file=sys.stderr)
        raise SystemExit(1)
    return sys.argv[1].rstrip("/")


def _normalize_callback_url(callback_url: str) -> str:
    if callback_url.endswith("/webhooks/trello"):
        return callback_url + "/"
    if callback_url.endswith("/webhooks/trello/"):
        return callback_url
    return f"{callback_url}/webhooks/trello/"


def _list_webhooks(trello_key: str, trello_token: str) -> list[dict]:
    url = f"https://api.trello.com/1/tokens/{trello_token}/webhooks"
    response = requests.get(url, params={"key": trello_key}, timeout=10)
    response.raise_for_status()
    return response.json()


def _delete_webhook(trello_key: str, trello_token: str, webhook_id: str) -> None:
    print(f"Deleting webhook {webhook_id}...")
    url = f"https://api.trello.com/1/webhooks/{webhook_id}"
    response = requests.delete(url, params={"key": trello_key, "token": trello_token}, timeout=10)
    response.raise_for_status()


def _create_webhook(trello_key: str, trello_token: str, board_id: str, callback_url: str) -> None:
    print(f"Creating webhook for {callback_url}...")
    url = "https://api.trello.com/1/webhooks"
    payload = {
        "key": trello_key,
        "token": trello_token,
        "callbackURL": callback_url,
        "idModel": board_id,
    }
    response = requests.post(url, data=payload, timeout=10)
    response.raise_for_status()


def main() -> int:
    _load_dotenv(".env")
    trello_key = _get_required_env("TRELLO_KEY")
    trello_token = _get_required_env("TRELLO_TOKEN")
    callback_url = _normalize_callback_url(_parse_args())

    if requests is None:
        print("Missing requests. Install with: python3 -m pip install requests", file=sys.stderr)
        return 1

    webhooks = _list_webhooks(trello_key, trello_token)
    board_id = _get_required_env("TRELLO_BOARD_ID")
    for webhook in webhooks:
        webhook_id = webhook.get("id")
        if webhook_id:
            _delete_webhook(trello_key, trello_token, webhook_id)
    print("Deleted previous webhooks.")
    _create_webhook(trello_key, trello_token, board_id, callback_url)
    print("Webhook created.")
    webhooks = _list_webhooks(trello_key, trello_token)
    sys.stdout.write(str(webhooks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
