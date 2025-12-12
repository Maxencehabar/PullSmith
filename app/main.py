from fastapi import FastAPI

from app.api import github, health, trello
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="AI Dev Orchestrator", version="0.1.0")

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(trello.router, prefix="/webhooks/trello", tags=["trello"])
app.include_router(github.router, prefix="/webhooks/github", tags=["github"])
