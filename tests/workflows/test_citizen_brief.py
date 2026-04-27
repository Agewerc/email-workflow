from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import AppSettings, WorkflowCatalog, WorkflowDefinition
from email_workflow.workflows.citizen_brief import CitizenBriefWorkflow


class DummyLLMProvider:
    def complete(self, prompt, config):
        if "Return this exact structure" in prompt:
            return type("Resp", (), {"text": "Here is the final brief.\n\n**News**\n- **Headline**\nContext", "input_tokens": 5, "output_tokens": 5})()
        return type("Resp", (), {"text": "- **Headline**\nContext", "input_tokens": 5, "output_tokens": 5})()


class DummyEmailProvider:
    def send_email(self, **kwargs):
        return True


class DummyGmailProvider:
    def gather_section(self, name, query, max_threads, account, body_max_chars):
        from email_workflow.schemas import ContentItem, SectionContent

        return SectionContent(
            name=name,
            items=[ContentItem(identifier="1", title="Subject", source="Sender", summary="Snippet", body="Body")],
        )


class DummyWeekendForecastProvider:
    pass


def test_citizen_brief_render_creates_email_artifacts(tmp_path: Path) -> None:
    definition = WorkflowDefinition(
        id="citizen-brief",
        workflow_type="citizen_brief",
        name="Citizen Brief",
        description="desc",
        config={
            "email_account": "test@example.com",
            "email_to": "test@example.com",
            "email_subject": "Test Brief",
            "model_provider": "deepseek",
            "models": {"deepseek": {"api_key_env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"}},
            "sections": [{"name": "News", "query": "label:test", "max_threads": 1}],
            "prompt_files": {
                "section": "config/prompts/citizen_brief_section.txt",
                "inbox": "config/prompts/citizen_brief_inbox.txt",
                "editor": "config/prompts/citizen_brief_editor.txt",
            },
            "template_html": "src/email_workflow/templates/digest.html.j2",
            "template_text": "src/email_workflow/templates/digest.txt.j2",
        },
    )
    ctx = WorkflowContext(
        settings=AppSettings(),
        catalog=WorkflowCatalog(workflows=[definition]),
        definition=definition,
        project_root=Path.cwd(),
        run_dir=tmp_path,
        prompt_dir=Path("config/prompts"),
        llm_provider=DummyLLMProvider(),
        email_provider=DummyEmailProvider(),
        gmail_provider=DummyGmailProvider(),
        weekend_forecast_provider=DummyWeekendForecastProvider(),
    )
    workflow = CitizenBriefWorkflow()
    result = workflow.run(ctx, dry_run=True)
    assert result.status.value == "success"
    assert (tmp_path / "email.html").exists()
    assert (tmp_path / "summaries.json").exists()
    html = (tmp_path / "email.html").read_text(encoding="utf-8")
    text = (tmp_path / "email.txt").read_text(encoding="utf-8")
    assert "**Headline**" not in html
    assert ">Headline<" in html
    assert "📰 News" in html
    assert "[ 📰 NEWS ]" in text
