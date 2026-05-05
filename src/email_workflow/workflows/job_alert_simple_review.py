"""Simplified job alert whole-pool review workflow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import JobAlertDigestWorkflowConfig, RenderedEmail, SectionContent, WorkflowContent, WorkflowMeta
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.job_alert_digest import JobAlertDigestWorkflow


class JobAlertSimpleReviewWorkflow(JobAlertDigestWorkflow):
    workflow_type = "job_alert_simple_review"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> JobAlertDigestWorkflowConfig:
        return JobAlertDigestWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def _review_prompt_path(self) -> Path:
        return resolve_project_path("config/prompts/job_alert_bucket_review.txt")

    def _format_candidate_pool(self, jobs) -> str:
        lines = []
        for index, job in enumerate(jobs, start=1):
            lines.append(
                "\n".join(
                    [
                        f"--- Job {index} ---",
                        f"Title: {job.title}",
                        f"Company: {job.company or 'Unknown'}",
                        f"Location: {job.location or 'Unknown'}",
                        f"Summary: {job.summary or 'No summary extracted.'}",
                        f"Link: {job.link or 'No direct link extracted.'}",
                        f"Source email: {job.source_email or 'Unknown'}",
                    ]
                )
            )
        return "\n\n".join(lines)

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        config = self.config(ctx)
        section = gathered.sections[0] if gathered.sections else SectionContent(name="Job Alerts", items=[])
        jobs = []
        for item in section.items:
            jobs.extend(self._extract_jobs_from_item(ctx, item))
        jobs = self._dedupe_jobs(jobs)

        candidates_artifact = ctx.artifact_path("candidates.json")
        candidates_artifact.write_text(
            json.dumps([job.model_dump(mode="json") for job in jobs], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["candidates"] = candidates_artifact

        review_pool = jobs[: min(len(jobs), 25)]
        prompt = self._review_prompt_path().read_text(encoding="utf-8").format(
            profile=self._read_profile(ctx),
            candidate_pool=self._format_candidate_pool(review_pool),
            target_functions=", ".join(config.target_functions) or "Not specified",
            target_industries=", ".join(config.target_industries) or "Not specified",
            target_locations=", ".join(config.target_locations) or "Not specified",
            inclusion_keywords=", ".join(config.inclusion_keywords) or "Not specified",
            exclusion_keywords=", ".join(config.exclusion_keywords) or "Not specified",
            seniority_keywords=", ".join(config.seniority_keywords) or "Not specified",
        )
        response = ctx.llm_provider.complete(prompt, config)
        raw_text = response.text.strip()
        raw_artifact = ctx.artifact_path("review_raw.txt")
        raw_artifact.write_text(raw_text, encoding="utf-8")
        ctx.artifacts["review_raw"] = raw_artifact

        names = ["Top Matches", "Worth a Look", "Not a Fit"]
        parsed = self._parse_editor_output(raw_text, names)
        final_sections = [SectionContent(name=name, summary=parsed[name] or "No strong items.") for name in names]
        return WorkflowContent(sections=final_sections, metadata={"raw_review": raw_text})

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        subject = "Job Alert Simple Review"
        date_label = datetime.now().strftime("%A, %d %B %Y")
        lines = [subject, f"Date: {date_label}", "=" * 60, ""]
        for section in content.sections:
            lines.append(f"[ ✦ {section.name.upper()} ]")
            lines.append(section.summary or "No strong items.")
            lines.append("")
        text = "\n".join(lines).strip()
        html = "<html><body><pre>" + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre></body></html>"
        html_artifact = ctx.artifact_path("email.html")
        html_artifact.write_text(html, encoding="utf-8")
        text_artifact = ctx.artifact_path("email.txt")
        text_artifact.write_text(text, encoding="utf-8")
        ctx.artifacts["email_html"] = html_artifact
        ctx.artifacts["email_text"] = text_artifact
        return RenderedEmail(subject=subject, html=html, text=text)
