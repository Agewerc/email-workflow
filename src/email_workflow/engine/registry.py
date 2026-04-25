"""Workflow registry."""

from __future__ import annotations

from collections.abc import Callable

from email_workflow.workflows.base import BaseWorkflow


WorkflowFactory = Callable[[], BaseWorkflow]


class WorkflowRegistry:
    """Map workflow types to workflow factories."""

    def __init__(self) -> None:
        self._factories: dict[str, WorkflowFactory] = {}

    def register(self, workflow_type: str, factory: WorkflowFactory) -> None:
        self._factories[workflow_type] = factory

    def create(self, workflow_type: str) -> BaseWorkflow:
        try:
            return self._factories[workflow_type]()
        except KeyError as exc:
            raise KeyError(f"Workflow type not registered: {workflow_type}") from exc

    def available_types(self) -> list[str]:
        return sorted(self._factories)
