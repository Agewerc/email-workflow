"""Lightweight scheduling metadata."""

from __future__ import annotations

from pydantic import BaseModel


class SchedulerEntry(BaseModel):
    workflow_id: str
    cadence: str = "manual"
    enabled: bool = True
