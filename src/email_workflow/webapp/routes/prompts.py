"""Prompt inspection and editing routes."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/prompts")


def _prompt_dir(request: Request) -> Path:
    return request.app.state.prompt_dir


@router.get("/", response_class=HTMLResponse)
def prompt_index(request: Request) -> HTMLResponse:
    prompt_dir = _prompt_dir(request)
    prompts = sorted(path.name for path in prompt_dir.glob("*.txt"))
    return request.app.state.templates.TemplateResponse(
        request,
        "prompt_index.html",
        {"prompts": prompts},
    )


@router.get("/{prompt_name}", response_class=HTMLResponse)
def prompt_editor(prompt_name: str, request: Request) -> HTMLResponse:
    prompt_path = _prompt_dir(request) / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    return request.app.state.templates.TemplateResponse(
        request,
        "prompt_editor.html",
        {"prompt_name": prompt_name, "content": prompt_path.read_text(encoding="utf-8")},
    )


@router.post("/{prompt_name}")
async def update_prompt(prompt_name: str, request: Request) -> RedirectResponse:
    prompt_path = _prompt_dir(request) / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    body = (await request.body()).decode("utf-8")
    content = parse_qs(body).get("content", [""])[0]
    prompt_path.write_text(content, encoding="utf-8")
    return RedirectResponse(url=f"/prompts/{prompt_name}", status_code=303)
