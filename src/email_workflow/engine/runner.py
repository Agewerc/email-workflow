"""Workflow runner and default registry setup."""

from __future__ import annotations

import json
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.engine.registry import WorkflowRegistry
from email_workflow.providers.content.gmail import GmailContentProvider
from email_workflow.providers.email.gmail_gog import GogEmailProvider
from email_workflow.providers.llm.deepseek import DeepSeekProvider
from email_workflow.schemas import AppSettings, WorkflowCatalog, load_workflow_catalog
from email_workflow.utils.dates import timestamp_slug
from email_workflow.utils.files import ensure_directory, project_root, resolve_project_path
from email_workflow.workflows import CitizenBriefWorkflow, SurfReportWorkflow, WeatherReportWorkflow


def create_default_registry() -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register("citizen_brief", CitizenBriefWorkflow)
    registry.register("surf_report", SurfReportWorkflow)
    registry.register("weather_report", WeatherReportWorkflow)
    return registry


class WorkflowRunner:
    """Load workflow definitions and execute a registered workflow."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        registry: WorkflowRegistry | None = None,
        catalog_path: Path | None = None,
        llm_provider=None,
        email_provider=None,
        gmail_provider=None,
    ) -> None:
        self.settings = settings or AppSettings()
        self.registry = registry or create_default_registry()
        self.root = project_root()
        self.catalog_path = catalog_path or self._default_catalog_path()
        self.catalog = load_workflow_catalog(self.catalog_path)
        self.llm_provider = llm_provider or DeepSeekProvider()
        self.email_provider = email_provider or GogEmailProvider()
        self.gmail_provider = gmail_provider or GmailContentProvider()

    def _default_catalog_path(self) -> Path:
        primary = resolve_project_path(self.settings.default_workflow_file)
        if primary.exists():
            return primary
        fallback = resolve_project_path("config/workflows.example.yaml")
        return fallback

    def list_workflows(self) -> list:
        return self.catalog.workflows

    def get_definition(self, workflow_id: str):
        return self.catalog.get(workflow_id)

    def make_run_dir(self, workflow_id: str) -> Path:
        base = ensure_directory(resolve_project_path(self.settings.run_dir))
        return ensure_directory(base / workflow_id / timestamp_slug())

    def run(self, workflow_id: str, *, dry_run: bool = False, skip_delivery: bool = False):
        definition = self.get_definition(workflow_id)
        workflow = self.registry.create(definition.workflow_type)
        run_dir = self.make_run_dir(workflow_id)
        prompt_dir = resolve_project_path(self.settings.default_prompt_dir)
        ctx = WorkflowContext(
            settings=self.settings,
            catalog=self.catalog,
            definition=definition,
            project_root=self.root,
            run_dir=run_dir,
            prompt_dir=prompt_dir,
            llm_provider=self.llm_provider,
            email_provider=self.email_provider,
            gmail_provider=self.gmail_provider,
        )
        result = workflow.run(ctx, dry_run=dry_run, skip_delivery=skip_delivery)
        (run_dir / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    def save_catalog(self) -> None:
        payload = self.catalog.model_dump(mode="json")
        self.catalog_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
