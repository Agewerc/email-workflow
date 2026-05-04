from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import AppSettings, WorkflowCatalog, WorkflowDefinition
from email_workflow.workflows.prof_g_insights import ProfGInsightsWorkflow


class DummyLLMProvider:
    def complete(self, prompt, config):
        assert "Prof G newsletter insight report" in prompt
        return type(
            "Resp",
            (),
            {
                "text": """[
                  {
                    "title": "AI capex is becoming a strategic concentration risk",
                    "conclusion": "The main conclusion is that large technology firms are turning AI infrastructure spend into a competitive moat, but the scale of investment also concentrates execution risk.",
                    "supporting_data_evidence": "The supplied Prof G email described hyperscaler investment in AI infrastructure and connected that spend to market expectations for durable growth.",
                    "considerations_watch_next": "Watch whether revenue from AI products starts matching infrastructure commitments, and whether smaller firms can compete without equivalent balance sheets.",
                    "source_emails": ["Prof G Markets: AI spending"]
                  }
                ]""",
                "input_tokens": 20,
                "output_tokens": 40,
            },
        )()


class DummyEmailProvider:
    def send_email(self, **kwargs):
        return True


class DummyGmailProvider:
    def gather_section(self, name, query, max_threads, account, body_max_chars):
        from email_workflow.schemas import ContentItem, SectionContent

        assert query == "label:newsletter-prof-g newer_than:7d"
        return SectionContent(
            name=name,
            items=[
                ContentItem(
                    identifier="thread-1",
                    title="Prof G Markets: AI spending",
                    source="newsletter@profgalloway.com",
                    summary="AI capex and market concentration.",
                    body="Hyperscalers are investing heavily in AI infrastructure, creating both moats and risk.",
                )
            ],
        )


class DummyWeekendForecastProvider:
    pass


def test_prof_g_insights_render_creates_structured_report(tmp_path: Path) -> None:
    definition = WorkflowDefinition(
        id="prof-g-insights",
        workflow_type="prof_g_insights",
        name="Prof G Weekly Insights",
        description="desc",
        config={
            "email_account": "test@example.com",
            "email_to": "test@example.com",
            "email_subject": "Weekly Prof G Insights",
            "model_provider": "deepseek",
            "models": {"deepseek": {"api_key_env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"}},
            "gmail_query": "label:newsletter-prof-g newer_than:7d",
            "prompt_files": {"synthesize": "config/prompts/prof_g_insights_synthesize.txt"},
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
    workflow = ProfGInsightsWorkflow()
    result = workflow.run(ctx, dry_run=True)

    assert result.status.value == "success"
    assert (tmp_path / "sources.json").exists()
    assert (tmp_path / "insights.json").exists()
    html = (tmp_path / "email.html").read_text(encoding="utf-8")
    text = (tmp_path / "email.txt").read_text(encoding="utf-8")
    assert "AI capex is becoming a strategic concentration risk" in html
    assert "Supporting data / evidence" in html
    assert "What to consider / watch next" in html
    assert "Prof G Markets: AI spending" in text
