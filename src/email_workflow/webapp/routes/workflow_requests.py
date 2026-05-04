"""Workflow request planning routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from email_workflow.utils.files import ensure_directory

router = APIRouter(prefix="/workflow-requests")


def _request_dir(request: Request) -> Path:
    return ensure_directory(request.app.state.workflow_request_dir)


def _safe_request_path(request_dir: Path, request_name: str) -> Path:
    safe_name = Path(request_name).name
    if safe_name != request_name:
        raise HTTPException(status_code=404, detail="Workflow request not found")
    if not safe_name.endswith(".md"):
        safe_name = f"{safe_name}.md"
    path = request_dir / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workflow request not found")
    return path


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "workflow-request"


def _unique_request_path(request_dir: Path, slug: str) -> Path:
    candidate = request_dir / f"{slug}.md"
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = request_dir / f"{slug}-{index}.md"
        if not candidate.exists():
            return candidate
        index += 1


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _request_entries(request_dir: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(request_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = _extract_title(content, path.stem.replace("-", " ").title())
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entries.append(
            {
                "name": path.name,
                "title": title,
                "href": f"/workflow-requests/{path.name}",
                "updated_at": updated_at,
            }
        )
    return entries


def _default_request_content(title: str, slug: str) -> str:
    created_on = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"# Workflow Request: {title}\n\n"
        "Status: Draft\n"
        f"Slug: {slug}\n"
        f"Created: {created_on}\n\n"
        "## What this workflow should do\n"
        "- Describe the job this workflow should perform.\n"
        "- Explain why it matters.\n\n"
        "## Trigger or frequency\n"
        "- When should it run?\n"
        "- Is it event-based, daily, weekly, or manual?\n\n"
        "## Inputs and data sources\n"
        "- Which emails, APIs, files, or signals should it use?\n\n"
        "## Output and delivery\n"
        "- What should the final output look like?\n"
        "- Who should receive it?\n\n"
        "## Rules and constraints\n"
        "- Include formatting rules, exclusions, priorities, and any guardrails.\n\n"
        "## Notes for Codex implementation\n"
        "- Add any extra instructions you want me to follow when you later ask me to build this workflow.\n"
    )


@router.get("/", response_class=HTMLResponse)
def workflow_request_index(request: Request) -> HTMLResponse:
    request_dir = _request_dir(request)
    entries = _request_entries(request_dir)
    return request.app.state.templates.TemplateResponse(
        request,
        "workflow_request_index.html",
        {
            "workflow_requests": entries,
            "request_count": len(entries),
        },
    )


@router.post("/new")
async def create_workflow_request(request: Request) -> RedirectResponse:
    request_dir = _request_dir(request)
    body = (await request.body()).decode("utf-8")
    payload = parse_qs(body)
    title = payload.get("title", [""])[0].strip()
    content = payload.get("content", [""])[0]
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    slug = _slugify(title)
    path = _unique_request_path(request_dir, slug)
    content_to_write = content.strip() or _default_request_content(title, path.stem)
    path.write_text(content_to_write, encoding="utf-8")
    return RedirectResponse(url=f"/workflow-requests/{path.name}", status_code=303)


@router.get("/{request_name}", response_class=HTMLResponse)
def workflow_request_editor(request_name: str, request: Request) -> HTMLResponse:
    request_dir = _request_dir(request)
    request_path = _safe_request_path(request_dir, request_name)
    content = request_path.read_text(encoding="utf-8")
    title = _extract_title(content, request_path.stem.replace("-", " ").title())
    return request.app.state.templates.TemplateResponse(
        request,
        "workflow_request_editor.html",
        {
            "request_name": request_path.name,
            "request_title": title,
            "content": content,
        },
    )


@router.post("/{request_name}")
async def update_workflow_request(request_name: str, request: Request) -> RedirectResponse:
    request_dir = _request_dir(request)
    request_path = _safe_request_path(request_dir, request_name)
    body = (await request.body()).decode("utf-8")
    content = parse_qs(body).get("content", [""])[0]
    request_path.write_text(content, encoding="utf-8")
    return RedirectResponse(url=f"/workflow-requests/{request_path.name}", status_code=303)
