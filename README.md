# AI Dev Agent

FastAPI orchestrator that turns Trello cards into automated Codex runs that clone a repo, apply changes, push a branch, open a PR, and update Trello.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or: pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Codex CLI must be installed and logged in (`codex exec` is invoked by the runner).

## Required env (.env)
- `TRELLO_KEY`, `TRELLO_TOKEN`, `TRELLO_BOARD_ID`
- `GITHUB_PAT` (push/PR on target repo)
- `OPENAI_API_KEY` (branch/commit suggestion; optional fallback exists)
- Optional: `OPENAI_MODEL` (default `gpt-4o-mini`)

## Trello → PR workflow
1) Create a card with:
   - Repo URL as the first attachment (or in the description as a URL).
   - Description starting with `Instructions :` followed by the task text.
   - Move the card to list `AI Ready`.
2) Webhook hits `/webhooks/trello/`. The orchestrator fetches the full card, skips cards not in `AI Ready`, already `WORKING`/`SUBMITTED`, or already in `.processed_cards`.
3) Runner clones the repo to `.tmp/`, runs `codex exec --sandbox workspace-write "<instructions>"`, and currently skips tests.
4) LLM suggests `feat/` or `fix/` branch + commit. If the branch exists remotely, it appends the Trello card id to avoid conflicts.
5) Commits, pushes with `GITHUB_PAT`, and opens a PR. Trello card is moved to `In Review`, label `SUBMITTED` is set, and a comment is added with the PR link.

## Notes
- Status labels expected on the board: `WORKING`, `SUBMITTED`. `PENDING` is not used.
- Processed Trello card ids are stored in `.processed_cards`; remove an id if you need to re-run it.
- GitHub webhook endpoint exists but the main flow is Trello → PR.
