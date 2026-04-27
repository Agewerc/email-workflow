"""CLI entry point for the email workflow platform."""

from __future__ import annotations

import json

import click
import uvicorn
from rich.console import Console
from rich.table import Table

from email_workflow.engine.runner import WorkflowRunner
from email_workflow.schemas import AppSettings
from email_workflow.utils.files import resolve_project_path
from email_workflow.utils.logging import configure_logging

console = Console()


@click.group()
def main() -> None:
    """Run and inspect email workflows."""


def _render_workflow_table() -> None:
    runner = WorkflowRunner()
    table = Table(title="Configured Workflows")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Enabled")
    table.add_column("Description")
    for workflow in runner.list_workflows():
        table.add_row(workflow.id, workflow.workflow_type, str(workflow.enabled), workflow.description)
    console.print(table)


@main.command("list-workflows")
def list_workflows() -> None:
    """List configured workflows."""

    _render_workflow_table()


@main.command("list")
def list_command() -> None:
    """List configured workflows."""

    _render_workflow_table()


@main.command("run")
@click.argument("workflow_id")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--skip-delivery", is_flag=True, default=False)
def run_workflow(workflow_id: str, dry_run: bool, skip_delivery: bool) -> None:
    """Run a workflow by id."""

    settings = AppSettings()
    configure_logging(settings.log_level, resolve_project_path(settings.log_dir))
    runner = WorkflowRunner(settings=settings)
    result = runner.run(workflow_id, dry_run=dry_run, skip_delivery=skip_delivery)
    console.print_json(data=json.loads(result.model_dump_json()))
    if result.status.value != "success":
        raise click.ClickException(result.message or "Workflow failed.")


@main.command("web")
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def run_web(host: str | None, port: int | None) -> None:
    """Run the admin web app."""

    settings = AppSettings()
    app_host = host or settings.webapp_host
    app_port = port or settings.webapp_port
    uvicorn.run("email_workflow.webapp.app:create_app", host=app_host, port=app_port, reload=settings.webapp_reload, factory=True)


if __name__ == "__main__":
    main()
