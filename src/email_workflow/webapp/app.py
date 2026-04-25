"""FastAPI admin app."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from email_workflow.utils.files import resolve_project_path
from email_workflow.webapp.routes import prompts, workflows


def create_app() -> FastAPI:
    app = FastAPI(title="Email Workflow Admin")
    templates = Jinja2Templates(directory=str(resolve_project_path("src/email_workflow/webapp/templates")))
    app.state.templates = templates
    app.state.prompt_dir = resolve_project_path("config/prompts")
    app.mount("/static", StaticFiles(directory=str(resolve_project_path("src/email_workflow/webapp/static"))), name="static")
    app.include_router(workflows.router)
    app.include_router(prompts.router)
    return app
