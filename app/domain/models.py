from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class JobState(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Task(BaseModel):
    source: str  # trello|github
    reference: str  # card id, issue id, etc.
    repo_url: HttpUrl
    branch: str = "main"
    description: str
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None


class Job(BaseModel):
    id: str
    task: Task
    state: JobState = JobState.pending
    logs: list[str] = []

    def add_log(self, message: str) -> None:
        self.logs.append(message)


class AiDevTask(BaseModel):
    task_id: str
    title: str
    description: str
    repos: list[str] = Field(default_factory=list)
    base_branch: str = "main"
    acceptance_criteria: list[str] = Field(default_factory=list)
