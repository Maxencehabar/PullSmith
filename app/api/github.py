import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import verify_signature
from app.domain.models import Task
from app.services.github_service import parse_github_pr
from app.services.orchestrator import Orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
_orchestrator = Orchestrator()


def get_orchestrator() -> Orchestrator:
    return _orchestrator


async def verify_github(x_hub_signature_256: str = Header(""), request: Request = None) -> None:
    settings = get_settings()
    body = await request.body()
    if not verify_signature(settings.github_webhook_secret, x_hub_signature_256, body, "sha256"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature")


@router.post("/", dependencies=[Depends(verify_github)])
async def github_webhook(request: Request, orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict:
    payload = await request.json()
    task: Task = parse_github_pr(payload)
    await orchestrator.start_worker()
    job = await orchestrator.submit_task(task)
    return {"job_id": job.id, "state": job.state}
