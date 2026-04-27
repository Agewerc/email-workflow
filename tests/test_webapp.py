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
