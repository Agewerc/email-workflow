"""Workflow execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from email_workflow.schemas import AppSettings, WorkflowCatalog, WorkflowDefinition

if TYPE_CHECKING:
    from email_workflow.providers.content.gmail import GmailContentProvider
    from email_workflow.providers.email.base import EmailProvider
    from email_workflow.providers.llm.base import LLMProvider


@dataclass(slots=True)
class WorkflowContext:
    settings: AppSettings
    catalog: WorkflowCatalog
    definition: WorkflowDefinition
    project_root: Path
    run_dir: Path
    prompt_dir: Path
    llm_provider: "LLMProvider"
    email_provider: "EmailProvider"
    gmail_provider: "GmailContentProvider"
    artifacts: dict[str, Path] = field(default_factory=dict)

    def artifact_path(self, name: str) -> Path:
        return self.run_dir / name
