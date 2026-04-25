from fastapi.testclient import TestClient

from email_workflow.webapp.app import create_app


def test_webapp_index_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "Email Workflow Platform" in response.text


def test_prompt_page_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/prompts/")
    assert response.status_code == 200
    assert "citizen_brief_section.txt" in response.text
