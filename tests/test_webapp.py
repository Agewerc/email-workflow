from pathlib import Path

from fastapi.testclient import TestClient

from email_workflow.webapp.app import create_app


def test_webapp_index_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "Workflow Control Center" in response.text
    assert "Configured Workflows" in response.text


def test_workflow_detail_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/workflows/citizen-brief")
    assert response.status_code == 200
    assert "Prompt Assets" in response.text
    assert "2026-01-01T09:00:00+08:00" in response.text


def test_prompt_page_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/prompts/")
    assert response.status_code == 200
    assert "citizen_brief_section.txt" in response.text


def test_workflow_request_page_loads(tmp_path: Path) -> None:
    request_path = tmp_path / "weekly-startup-digest.md"
    request_path.write_text("# Workflow Request: Weekly Startup Digest\n", encoding="utf-8")
    app = create_app()
    app.state.workflow_request_dir = tmp_path
    client = TestClient(app)
    response = client.get("/workflow-requests/")
    assert response.status_code == 200
    assert "Workflow Requests" in response.text
    assert "Weekly Startup Digest" in response.text


def test_workflow_request_can_be_created(tmp_path: Path) -> None:
    app = create_app()
    app.state.workflow_request_dir = tmp_path
    client = TestClient(app)
    response = client.post(
        "/workflow-requests/new",
        data={"title": "Inbox Priorities Brief", "content": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Inbox Priorities Brief" in response.text
    created = tmp_path / "inbox-priorities-brief.md"
    assert created.exists()
    assert "## What this workflow should do" in created.read_text(encoding="utf-8")
