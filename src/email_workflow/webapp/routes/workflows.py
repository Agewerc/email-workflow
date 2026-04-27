"""Workflow inspection routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from email_workflow.engine.runner import WorkflowRunner

router = APIRouter()


def _labelize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _prompt_entries(prompt_dir: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    prompt_files = config.get("prompt_files", {})
    if not isinstance(prompt_files, dict):
        return []
    entries: list[dict[str, Any]] = []
    for role, path in sorted(prompt_files.items()):
        filename = Path(path).name
        local_path = prompt_dir / filename
        entries.append(
            {
                "role": _labelize(role),
                "path": path,
                "filename": filename,
                "href": f"/prompts/{filename}" if local_path.exists() else None,
            }
        )
    return entries


def _config_summary(config: dict[str, Any]) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []
    preferred_keys = [
        "email_to",
        "email_account",
        "email_subject",
        "model_provider",
        "timezone",
        "schedule_day",
        "schedule_time",
        "schedule_timezone",
        "forecast_days",
        "weather_source_label",
        "surf_source_label",
        "template_html",
        "template_text",
    ]
    for key in preferred_keys:
        if key in config and _is_scalar(config[key]):
            summary.append({"label": _labelize(key), "value": str(config[key])})
    return summary


def _config_blocks(config: dict[str, Any]) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for key, value in sorted(config.items()):
        if key == "prompt_files" or _is_scalar(value):
            continue
        blocks.append(
            {
                "label": _labelize(key),
                "value": json.dumps(value, indent=2, sort_keys=True),
            }
        )
    return blocks


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    runner = WorkflowRunner()
    workflows = runner.list_workflows()
    return request.app.state.templates.TemplateResponse(
        request,
        "index.html",
        {
            "workflows": workflows,
            "workflow_count": len(workflows),
            "enabled_count": sum(1 for workflow in workflows if workflow.enabled),
        },
    )


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
def workflow_detail(workflow_id: str, request: Request) -> HTMLResponse:
    runner = WorkflowRunner()
    definition = runner.get_definition(workflow_id)
    prompt_dir = request.app.state.prompt_dir
    return request.app.state.templates.TemplateResponse(
        request,
        "workflow_detail.html",
        {
            "workflow": definition,
            "config_json": json.dumps(definition.config, indent=2),
            "summary_items": _config_summary(definition.config),
            "config_blocks": _config_blocks(definition.config),
            "prompt_entries": _prompt_entries(prompt_dir, definition.config),
        },
    )
