"""Weekly Prof G newsletter insight workflow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.renderers import render_digest_html, render_digest_text
from email_workflow.schemas import (
    ContentItem,
    InsightItem,
    ProfGInsightsWorkflowConfig,
    RenderedEmail,
    SectionContent,
    WorkflowContent,
    WorkflowMeta,
)
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.base import BaseWorkflow


class ProfGInsightsWorkflow(BaseWorkflow):
    workflow_type = "prof_g_insights"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> ProfGInsightsWorkflowConfig:
        return ProfGInsightsWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def _prompt_path(self, ctx: WorkflowContext, key: str) -> Path:
        config = self.config(ctx)
        return resolve_project_path(config.prompt_files[key])

    def _read_prompt(self, ctx: WorkflowContext, key: str) -> str:
        return self._prompt_path(ctx, key).read_text(encoding="utf-8").strip()

    def _extract_json_block(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                decoder = json.JSONDecoder()
                _, end = decoder.raw_decode(stripped)
                return stripped[:end]
            except json.JSONDecodeError:
                pass
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                _, end = decoder.raw_decode(text[index:])
                return text[index : index + end]
            except json.JSONDecodeError:
                continue
        return "[]"

    def _format_items_for_prompt(self, items: list[ContentItem], body_max_chars: int) -> str:
        blocks = []
        for index, item in enumerate(items, start=1):
            content = item.body if len(item.body) > len(item.summary) else item.summary
            blocks.append(
                "\n".join(
                    [
                        f"--- Email {index} ---",
                        f"Subject: {item.title}",
                        f"From: {item.source}",
                        f"Date: {item.published_at}",
                        f"Thread ID: {item.identifier}",
                        f"Snippet: {item.summary}",
                        f"Content: {content[:body_max_chars]}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        config = self.config(ctx)
        section = ctx.gmail_provider.gather_section(
            "Prof G Emails",
            config.gmail_query,
            config.max_threads,
            config.email_account,
            config.body_max_chars,
        )
        content = WorkflowContent(sections=[section])
        artifact = ctx.artifact_path("sources.json")
        artifact.write_text(content.model_dump_json(indent=2), encoding="utf-8")
        ctx.artifacts["sources"] = artifact
        return content

    def _parse_insights(self, text: str, config: ProfGInsightsWorkflowConfig) -> list[InsightItem]:
        payload = self._extract_json_block(text)
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            return []
        insights: list[InsightItem] = []
        for item in parsed[: config.max_insights]:
            if not isinstance(item, dict) or not str(item.get("title", "")).strip():
                continue
            insights.append(
                InsightItem(
                    title=str(item.get("title", "")).strip(),
                    conclusion=str(item.get("conclusion", "")).strip(),
                    supporting_data_evidence=str(item.get("supporting_data_evidence", "")).strip(),
                    considerations_watch_next=str(item.get("considerations_watch_next", "")).strip(),
                    source_emails=[str(source).strip() for source in item.get("source_emails", []) if str(source).strip()],
                    metadata={"raw": item},
                )
            )
        return insights

    def _insight_to_section(self, insight: InsightItem) -> SectionContent:
        summary_lines = [
            f"**Conclusion:** {insight.conclusion or 'No clear conclusion provided.'}",
            "",
            f"**Supporting data / evidence:** {insight.supporting_data_evidence or 'No explicit supporting evidence provided.'}",
            "",
            f"**What to consider / watch next:** {insight.considerations_watch_next or 'No next watch item provided.'}",
        ]
        if insight.source_emails:
            summary_lines.extend(["", "**Source emails:** " + "; ".join(insight.source_emails)])
        return SectionContent(name=insight.title[:90], summary="\n".join(summary_lines), metadata=insight.model_dump(mode="json"))

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        config = self.config(ctx)
        section = gathered.sections[0] if gathered.sections else SectionContent(name="Prof G Emails", items=[])
        if not section.items:
            empty = SectionContent(
                name="No Prof G Emails Found",
                summary="NO_STRONG_ITEMS",
                metadata={"query": config.gmail_query},
            )
            return WorkflowContent(sections=[empty], metadata={"insights": []})

        prompt = self._read_prompt(ctx, "synthesize").format(
            max_insights=config.max_insights,
            emails=self._format_items_for_prompt(section.items, config.body_max_chars),
        )
        response = ctx.llm_provider.complete(prompt, config)
        raw_artifact = ctx.artifact_path("llm_response.txt")
        raw_artifact.write_text(response.text, encoding="utf-8")
        ctx.artifacts["llm_response"] = raw_artifact

        insights = self._parse_insights(response.text, config)
        sections = [self._insight_to_section(insight) for insight in insights]
        if not sections:
            sections = [SectionContent(name="Prof G Weekly Readout", summary="NO_STRONG_ITEMS")]

        insights_artifact = ctx.artifact_path("insights.json")
        insights_artifact.write_text(
            json.dumps([insight.model_dump(mode="json") for insight in insights], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["insights"] = insights_artifact

        summaries_artifact = ctx.artifact_path("summaries.json")
        summaries_artifact.write_text(
            json.dumps({section.name: section.summary for section in sections}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["summaries"] = summaries_artifact
        return WorkflowContent(
            sections=sections,
            metadata={"insights": [insight.model_dump(mode="json") for insight in insights]},
        )

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        config = self.config(ctx)
        date_label = datetime.now().strftime("%A, %d %B %Y")
        html = render_digest_html(
            resolve_project_path(config.template_html),
            subject=config.email_subject,
            heading="Weekly Prof G Insights",
            date_label=date_label,
            footer_label="Generated by Email Workflow Platform",
            sections=content.sections,
        )
        text = render_digest_text(
            resolve_project_path(config.template_text),
            subject=config.email_subject,
            date_label=date_label,
            footer_label="Generated by Email Workflow Platform",
            sections=content.sections,
        )
        html_artifact = ctx.artifact_path("email.html")
        html_artifact.write_text(html, encoding="utf-8")
        text_artifact = ctx.artifact_path("email.txt")
        text_artifact.write_text(text, encoding="utf-8")
        ctx.artifacts["email_html"] = html_artifact
        ctx.artifacts["email_text"] = text_artifact
        return RenderedEmail(subject=config.email_subject, html=html, text=text)
