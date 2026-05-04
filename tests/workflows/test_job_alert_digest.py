from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.renderers.html import render_inline_markdown, render_summary_html
from email_workflow.schemas import AppSettings, ContentItem, JobOpportunity, WorkflowCatalog, WorkflowDefinition
from email_workflow.workflows.job_alert_digest import JobAlertDigestWorkflow


class DummyLLMProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt, config):
        self.calls += 1
        if "Return only valid JSON" in prompt:
            if "scoring multiple job opportunities" in prompt.lower():
                return type(
                    "Resp",
                    (),
                    {
                        "text": '[{"score": 92, "rationale": "Strong senior AI and mining fit for Alan based on the profile."}]',
                        "input_tokens": 8,
                        "output_tokens": 12,
                    },
                )()
            return type(
                "Resp",
                (),
                {
                    "text": '[{"title":"Principal Data Scientist","company":"Acme Mining","location":"Perth","link":"https://example.com/job","summary":"Lead AI and analytics programs."}]',
                    "input_tokens": 8,
                    "output_tokens": 12,
                },
            )()
        return type(
            "Resp",
            (),
            {
                "text": "Top Matches\n**Principal Data Scientist** – Acme Mining – Perth\nStrong senior fit with mining and AI overlap.\nLink: https://example.com/job\n\nWorth a Look\nNO_STRONG_ITEMS\n\nMaybe / Lower Fit\nNO_STRONG_ITEMS",
                "input_tokens": 10,
                "output_tokens": 20,
            },
        )()


class DummyEmailProvider:
    def send_email(self, **kwargs):
        return True


class DummyGmailProvider:
    def gather_section(self, name, query, max_threads, account, body_max_chars):
        from email_workflow.schemas import ContentItem, SectionContent

        return SectionContent(
            name=name,
            items=[
                ContentItem(
                    identifier="thread-1",
                    title="New jobs for Principal Data Scientist",
                    source="alerts@example.com",
                    summary="Principal Data Scientist at Acme Mining",
                    body="Principal Data Scientist role in Perth. Acme Mining. https://example.com/job",
                )
            ],
        )


class DummyWeekendForecastProvider:
    pass


def test_job_alert_digest_render_creates_artifacts(tmp_path: Path) -> None:
    profile_path = tmp_path / "alan_profile.md"
    profile_path.write_text("Alan is a senior data and AI leader focused on mining and applied analytics.", encoding="utf-8")
    definition = WorkflowDefinition(
        id="job-alert-digest",
        workflow_type="job_alert_digest",
        name="Job Alert Digest",
        description="desc",
        config={
            "email_account": "test@example.com",
            "email_to": "test@example.com",
            "email_subject": "Job Alert Digest",
            "model_provider": "deepseek",
            "models": {"deepseek": {"api_key_env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"}},
            "gmail_query": 'label:"Jobs" newer_than:1d',
            "inclusion_keywords": ["data science", "ai"],
            "seniority_keywords": ["principal", "lead"],
            "target_industries": ["mining"],
            "target_locations": ["perth"],
            "profile_file": str(profile_path),
            "prompt_files": {
                "extract": "config/prompts/job_alert_extract.txt",
                "score": "config/prompts/job_alert_score.txt",
                "editor": "config/prompts/job_alert_editor.txt",
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
    workflow = JobAlertDigestWorkflow()
    result = workflow.run(ctx, dry_run=True)
    assert result.status.value == "success"
    assert (tmp_path / "jobs.json").exists()
    html = (tmp_path / "email.html").read_text(encoding="utf-8")
    text = (tmp_path / "email.txt").read_text(encoding="utf-8")
    assert "Principal Data Scientist" in html
    assert '<a href="https://example.com/job" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;"><strong>Principal Data Scientist</strong> <span style="font-weight:700;">↗</span></a>' in html
    assert "Link: " not in html
    assert "Top Matches" in html
    assert "[ ✦ TOP MATCHES ]" in text
    jobs = (tmp_path / "jobs.json").read_text(encoding="utf-8")
    assert '"score": 92' in jobs
    assert "Strong senior AI and mining fit for Alan" in jobs
    assert ctx.llm_provider.calls == 3


def test_render_inline_markdown_autolinks_link_label_urls() -> None:
    rendered = str(render_inline_markdown("Link: https://example.com/job?x=1&y=2"))
    assert 'Link: <a href="https://example.com/job?x=1&amp;y=2"' in rendered


def test_render_summary_html_links_the_job_title_from_following_link_line() -> None:
    rendered = str(
        render_summary_html(
            "**Principal Data Scientist** – Acme Mining – Perth\nLink: https://example.com/job?x=1&y=2"
        )
    )
    assert '<a href="https://example.com/job?x=1&amp;y=2" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;"><strong>Principal Data Scientist</strong> <span style="font-weight:700;">↗</span></a>' in rendered
    assert "Link:" not in rendered


def test_render_summary_html_links_the_job_title_from_inline_markdown_link() -> None:
    rendered = str(
        render_summary_html(
            "**Principal Data Scientist** – Acme Mining – Perth. Strong fit. [Link](https://example.com/job?x=1&y=2)"
        )
    )
    assert '<a href="https://example.com/job?x=1&amp;y=2" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;"><strong>Principal Data Scientist</strong> <span style="font-weight:700;">↗</span></a>' in rendered
    assert ">Link<" not in rendered


def test_render_summary_html_links_the_job_title_from_raw_url_line() -> None:
    rendered = str(
        render_summary_html(
            "**Principal Data Scientist** – Acme Mining – Perth\nStrong fit.\nhttps://example.com/job?x=1&y=2"
        )
    )
    assert '<a href="https://example.com/job?x=1&amp;y=2" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;"><strong>Principal Data Scientist</strong> <span style="font-weight:700;">↗</span></a>' in rendered
    assert ">https://example.com/job" not in rendered


def test_render_summary_html_links_the_job_title_from_markdown_link_only_line() -> None:
    rendered = str(
        render_summary_html(
            "**Principal Data Scientist** – Acme Mining – Perth\nStrong fit.\n[Link](https://example.com/job?x=1&y=2)"
        )
    )
    assert '<a href="https://example.com/job?x=1&amp;y=2" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;"><strong>Principal Data Scientist</strong> <span style="font-weight:700;">↗</span></a>' in rendered
    assert ">Link<" not in rendered


def test_job_alert_digest_rejects_malformed_extracted_titles() -> None:
    workflow = JobAlertDigestWorkflow()
    assert workflow._is_plausible_job(
        JobOpportunity(title="Principal Data Scientist", company="Acme Mining", location="Perth")
    )
    assert not workflow._is_plausible_job(
        JobOpportunity(title="* High-impact, data-driven role", company="", location="Perth")
    )
    assert not workflow._is_plausible_job(
        JobOpportunity(title="Meaningful work with broad organisational reach", company="", location="Perth")
    )
    assert not workflow._is_plausible_job(
        JobOpportunity(title="Level 6, $120,457 - $132,753 pa plus 12% super", company="", location="Perth")
    )


def test_job_alert_digest_filters_low_scores_before_editor() -> None:
    config = type("Config", (), {"min_digest_score": 55, "max_digest_jobs": 10})()
    jobs = [
        JobOpportunity(title="Principal Data Scientist", score=91),
        JobOpportunity(title="Pricing Analyst", score=41),
        JobOpportunity(title="Junior Consultant Analytics", score=18),
    ]
    workflow = JobAlertDigestWorkflow()

    shortlisted = workflow._shortlist_jobs(sorted(jobs, key=lambda job: job.score, reverse=True), config)

    assert [job.title for job in shortlisted] == ["Principal Data Scientist"]


def test_job_alert_digest_normalizes_five_point_llm_scores() -> None:
    workflow = JobAlertDigestWorkflow()
    assert workflow._normalize_llm_score(5) == 90
    assert workflow._normalize_llm_score(4) == 70
    assert workflow._normalize_llm_score(3) == 45
    assert workflow._normalize_llm_score(92) == 92


def test_job_alert_digest_normalizes_fallback_rule_scores() -> None:
    workflow = JobAlertDigestWorkflow()
    assert workflow._normalize_rule_score(5) == 75
    assert workflow._normalize_rule_score(4) == 50
    assert workflow._normalize_rule_score(1) == 10
    assert workflow._normalize_rule_score(7) == 85


def test_job_alert_digest_structured_fallback_extracts_linkedin_alert() -> None:
    workflow = JobAlertDigestWorkflow()
    item = ContentItem(
        identifier="thread-1",
        title="Principal Analytics Engineer at Mantel",
        source="LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>",
        body="""Your job alert for data scientist in Perth

Principal Analytics Engineer
Mantel
Perth, WA

This company is actively hiring
View job: https://www.linkedin.com/comm/jobs/view/4407328725/?trackingId=abc
""",
    )

    jobs = workflow._extract_structured_jobs_from_item(item, max_jobs=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Principal Analytics Engineer"
    assert jobs[0].company == "Mantel"
    assert jobs[0].location == "Perth, WA"


def test_job_alert_digest_structured_fallback_extracts_seek_alert() -> None:
    workflow = JobAlertDigestWorkflow()
    item = ContentItem(
        identifier="thread-1",
        title="18 new jobs for data scientist in Perth WA 6000",
        source="SEEK Job Alerts <jobmail@s.seek.com.au>",
        body="""logo

Data Scientist
Akkodis

Perth WA

[https://www.seek.com.au/job/91857581?savedSearchID=abc]
""",
    )

    jobs = workflow._extract_structured_jobs_from_item(item, max_jobs=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Data Scientist"
    assert jobs[0].company == "Akkodis"
    assert jobs[0].location == "Perth WA"
