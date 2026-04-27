from pathlib import Path

from email_workflow.engine.runner import WorkflowRunner
from email_workflow.schemas import AppSettings


class FakeLLMProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt, config):
        self.calls += 1
        if "Return this exact structure" in prompt:
            return type("Resp", (), {"text": "News\n**Lead story**\nOne sentence.\n\nInbox Highlights\nNO_STRONG_ITEMS", "input_tokens": 10, "output_tokens": 6})()
        return type("Resp", (), {"text": "**Lead story**\nOne sentence.", "input_tokens": 10, "output_tokens": 6})()


class FakeEmailProvider:
    def __init__(self) -> None:
        self.sent = False

    def send_email(self, **kwargs):
        self.sent = True
        return True


class FakeGmailProvider:
    def gather_section(self, name, query, max_threads, account, body_max_chars):
        from email_workflow.schemas import ContentItem, SectionContent

        item = ContentItem(identifier=f"{name}-1", title="Subject", source="Sender", summary="Snippet", body="Body")
        return SectionContent(name=name, items=[] if name == "Inbox Highlights" else [item])


def test_runner_executes_citizen_brief_with_fake_providers(tmp_path: Path) -> None:
    settings = AppSettings(default_workflow_file=str(tmp_path / "workflows.yaml"), default_prompt_dir="config/prompts", run_dir=str(tmp_path / "runs"), log_dir=str(tmp_path / "logs"))
    catalog_path = tmp_path / "workflows.yaml"
    catalog_path.write_text(
        """
workflows:
  - id: citizen-brief
    workflow_type: citizen_brief
    enabled: true
    frequency: "2026-01-01T09:00:00+08:00"
    name: Citizen Brief
    description: test
    config:
      email_account: test@example.com
      email_to: test@example.com
      email_subject: Test Brief
      model_provider: deepseek
      models:
        deepseek:
          api_key_env: DEEPSEEK_API_KEY
          base_url: https://api.deepseek.com/v1
          model: deepseek-chat
      sections:
        - name: News
          query: label:test
          max_threads: 1
      inbox_section:
        enabled: true
        name: Inbox Highlights
        query: newer_than:1d
        max_threads: 1
      prompt_files:
        section: config/prompts/citizen_brief_section.txt
        inbox: config/prompts/citizen_brief_inbox.txt
        editor: config/prompts/citizen_brief_editor.txt
      template_html: src/email_workflow/templates/digest.html.j2
      template_text: src/email_workflow/templates/digest.txt.j2
""".strip(),
        encoding="utf-8",
    )

    runner = WorkflowRunner(
        settings=settings,
        catalog_path=catalog_path,
        llm_provider=FakeLLMProvider(),
        email_provider=FakeEmailProvider(),
        gmail_provider=FakeGmailProvider(),
    )
    result = runner.run("citizen-brief", dry_run=True)
    assert result.status.value == "success"
    assert "run_dir" in result.output
