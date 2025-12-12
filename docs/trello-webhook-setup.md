# Trello Webhook Setup

This repo exposes a Trello webhook at `/webhooks/trello/` via FastAPI. The webhook only processes `updateCard` events where a card moves into the list named `AI Ready`.

## Prerequisites
- App is running and reachable at `https://<your-host>/webhooks/trello/` (use `ngrok http 8000` for local).
- Trello account with admin access on the board.
- The repo URL attached to cards (first attachment is treated as the repo to clone).

## Create the webhook
1) Go to https://trello.com/app-key and copy your API key.  
2) Click “Token” to generate a token for your account; copy it.  
3) POST to Trello’s webhook API:
```bash
curl -X POST https://api.trello.com/1/webhooks \
  -d "key=$TRELLO_KEY" \
  -d "token=$TRELLO_TOKEN" \
  -d "callbackURL=https://<your-host>/webhooks/trello/" \
  -d "idModel=<board-id>"
```
- `idModel` is the board ID (open the board in a browser, add `.json` to the URL to find `id`).  
- For local dev: `callbackURL` should be your tunnel URL (e.g., `https://<ngrok-id>.ngrok.io/webhooks/trello/`).

## What the webhook expects
- Header: `X-Trello-Webhook` must be present (currently only presence is checked; add a secret later). Trello includes this header automatically when you set one while creating the webhook.
- Payload: `action.type` must be `updateCard`, and `action.data.listAfter.name` must equal `AI Ready`; otherwise the request is ignored.

## Card requirements for an actionable task
- Attach the target repo URL to the card (first attachment is used).
- Add checklist items for acceptance criteria (optional; they become `acceptance_criteria`).
- The card name/description become the task title/description.

## Verifying locally
1) Start the app: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.  
2) Start a tunnel: `ngrok http 8000` and note the HTTPS URL.  
3) Create the webhook with `callbackURL` set to the tunnel.  
4) Move a card into the `AI Ready` list; check app logs for enqueue/run events.

## Hardening (optional)
- Add a shared secret and validate `X-Trello-Webhook` properly in `app/api/trello.py`.
- Persist jobs to a real queue (Redis) instead of running inline in `enqueue_task`.
- Add logging/metrics for webhook deliveries and failures.
