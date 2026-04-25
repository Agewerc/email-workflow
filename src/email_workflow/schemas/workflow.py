"""Workflow execution schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class RenderedEmail(BaseModel):
    subject: str
    html: str
    text: str


class WorkflowResult(BaseModel):
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    message: str = ""
    items_processed: int = 0
    errors: list[str] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)

    def mark_done(self, status: WorkflowStatus, message: str = "") -> None:
        self.finished_at = datetime.now(timezone.utc)
        self.status = status
        if message:
            self.message = message

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()
