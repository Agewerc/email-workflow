"""Experimental whole-pool LLM review for job alerts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import (
    JobAlertDigestWorkflowConfig,
    JobOpportunity,
    RenderedEmail,
    SectionContent,
    WorkflowContent,
    WorkflowMeta,
)
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.base import BaseWorkflow
from email_workflow.workflows.job_alert_digest import JobAlertDigestWorkflow


class JobAlertWholePoolExperimentWorkflow(JobAlertDigestWorkflow):
    workflow_type = "job_alert_whole_pool_experiment"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> JobAlertDigestWorkflowConfig:
        return JobAlertDigestWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def _format_candidate_pool(self, jobs: list[JobOpportunity]) -> str:
        lines: list[str] = []
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

    def _bucket_prompt_path(self, ctx: WorkflowContext) -> Path:
        return resolve_project_path("config/prompts/job_alert_bucket_review.txt")

    def _review_whole_pool(self, ctx: WorkflowContext, jobs: list[JobOpportunity]) -> dict:
        config = self.config(ctx)
        prompt = self._bucket_prompt_path(ctx).read_text(encoding="utf-8").format(
            profile=self._read_profile(ctx),
            candidate_pool=self._format_candidate_pool(jobs),
            target_functions=", ".join(config.target_functions) or "Not specified",
            target_industries=", ".join(config.target_industries) or "Not specified",
            target_locations=", ".join(config.target_locations) or "Not specified",
            inclusion_keywords=", ".join(config.inclusion_keywords) or "Not specified",
            exclusion_keywords=", ".join(config.exclusion_keywords) or "Not specified",
            seniority_keywords=", ".join(config.seniority_keywords) or "Not specified",
        )
        response = ctx.llm_provider.complete(prompt, config)
        raw_text = response.text.strip()
        review_debug = ctx.artifact_path("whole_pool_review_raw.txt")
        review_debug.write_text(raw_text, encoding="utf-8")
        ctx.artifacts["whole_pool_review_raw"] = review_debug
        cleaned = raw_text
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json") :].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```") :].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        payload = self._extract_json_block(cleaned)
        parsed = json.loads(payload)
        if isinstance(parsed, list):
            parsed = {
                "summary": "Model returned a list instead of bucket object; treating all items as worth a look.",
                "top_matches": [],
                "worth_a_look": parsed,
                "not_a_fit": [],
            }
        if not isinstance(parsed, dict):
            raise ValueError("Whole-pool review did not return an object")
        return parsed

    def _normalize_bucket_items(self, raw_items: list[dict], source_jobs: list[JobOpportunity]) -> list[JobOpportunity]:
        normalized: list[JobOpportunity] = []
        source_map = {(job.title.lower(), job.company.lower(), job.location.lower()): job for job in source_jobs}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            title = self._clean_text_field(item.get("title"))
            company = self._clean_text_field(item.get("company"))
            location = self._clean_text_field(item.get("location"))
            rationale = self._clean_text_field(item.get("rationale"))
            link = self._clean_text_field(item.get("link"))
            key = (title.lower(), company.lower(), location.lower())
            source = source_map.get(key)
            summary = source.summary if source else ""
            normalized.append(
                JobOpportunity(
                    title=title,
                    company=company,
                    location=location,
                    link=link or (source.link if source else ""),
                    summary=summary,
                    source_email=source.source_email if source else "",
                    relevance_reason=rationale,
                    score=source.score if source else 0,
                    metadata=source.metadata if source else {},
                )
            )
        return self._dedupe_jobs([job for job in normalized if job.title])

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        config = self.config(ctx)
        section = gathered.sections[0] if gathered.sections else SectionContent(name="Job Alerts", items=[])
        jobs: list[JobOpportunity] = []

        for item in section.items:
            extracted = self._extract_jobs_from_item(ctx, item)
            jobs.extend(extracted)
        jobs = self._dedupe_jobs(jobs)

        candidates_artifact = ctx.artifact_path("whole_pool_candidates.json")
        candidates_artifact.write_text(
            json.dumps([job.model_dump(mode="json") for job in jobs], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["whole_pool_candidates"] = candidates_artifact

        review_pool = jobs[: min(len(jobs), 25)]
        reviewed = self._review_whole_pool(ctx, review_pool)

        review_artifact = ctx.artifact_path("whole_pool_review.json")
        review_artifact.write_text(json.dumps(reviewed, indent=2, ensure_ascii=False), encoding="utf-8")
        ctx.artifacts["whole_pool_review"] = review_artifact

        top_jobs = self._normalize_bucket_items(reviewed.get("top_matches", []), review_pool)
        worth_jobs = self._normalize_bucket_items(reviewed.get("worth_a_look", []), review_pool)
        not_fit_jobs = self._normalize_bucket_items(reviewed.get("not_a_fit", []), review_pool)

        final_sections = [
            SectionContent(name="Top Matches", summary=self._fallback_section_summary(top_jobs)),
            SectionContent(name="Worth a Look", summary=self._fallback_section_summary(worth_jobs)),
            SectionContent(name="Not a Fit", summary=self._fallback_section_summary(not_fit_jobs)),
        ]
        return WorkflowContent(
            sections=final_sections,
            metadata={
                "summary": reviewed.get("summary", ""),
                "top_matches": [job.model_dump(mode="json") for job in top_jobs],
                "worth_a_look": [job.model_dump(mode="json") for job in worth_jobs],
                "not_a_fit": [job.model_dump(mode="json") for job in not_fit_jobs],
            },
        )

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        subject = "Job Alert Whole-Pool Experiment"
        date_label = datetime.now().strftime("%A, %d %B %Y")
        summary = content.metadata.get("summary", "")
        lines = [subject, f"Date: {date_label}", "=" * 60, "", summary, ""]
        for section in content.sections:
            lines.append(f"[ ✦ {section.name.upper()} ]")
            lines.append(section.summary or "NO_STRONG_ITEMS")
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
