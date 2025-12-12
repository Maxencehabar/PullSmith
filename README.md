# AI Dev Agent

FastAPI-based orchestrator that receives Trello and GitHub webhooks, normalizes work into jobs, and hands execution to an isolated runner that drives Codex.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Webhooks
- Trello: POST `/webhooks/trello/` with `X-Trello-Webhook` header set to `trello_webhook_secret`.
- GitHub: POST `/webhooks/github/` with `X-Hub-Signature-256` HMAC of the payload using `github_webhook_secret`.

## Workflow
1. Webhook payload is parsed into a `Task`.
2. Orchestrator enqueues a job to the in-memory worker.
3. Runner clones the repo, calls Codex, runs tests, and updates status (hooks for PR updates included).

## Environment
Configure `.env` with Trello and GitHub secrets, repo root, and optional queue/runner settings. See `app/core/config.py` for available keys.
