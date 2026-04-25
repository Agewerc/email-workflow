"""Workflow inspection routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from email_workflow.engine.runner import WorkflowRunner

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    runner = WorkflowRunner()
    return request.app.state.templates.TemplateResponse(
        request,
        "index.html",
        {"workflows": runner.list_workflows()},
    )


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
def workflow_detail(workflow_id: str, request: Request) -> HTMLResponse:
    runner = WorkflowRunner()
    definition = runner.get_definition(workflow_id)
    return request.app.state.templates.TemplateResponse(
        request,
        "workflow_detail.html",
        {
            "workflow": definition,
            "config_json": json.dumps(definition.config, indent=2),
        },
    )
