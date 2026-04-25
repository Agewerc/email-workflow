"""Citizen Brief workflow implementation."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.renderers import render_digest_html, render_digest_text
from email_workflow.schemas import (
    CitizenBriefWorkflowConfig,
    ContentItem,
    RenderedEmail,
    SectionContent,
    WorkflowContent,
    WorkflowMeta,
)
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.base import BaseWorkflow

logger = logging.getLogger(__name__)


class CitizenBriefWorkflow(BaseWorkflow):
    workflow_type = "citizen_brief"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> CitizenBriefWorkflowConfig:
        return CitizenBriefWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def _prompt_path(self, ctx: WorkflowContext, key: str) -> Path:
        config = self.config(ctx)
        relative = config.prompt_files[key]
        return resolve_project_path(relative)

    def _read_prompt(self, ctx: WorkflowContext, key: str) -> str:
        return self._prompt_path(ctx, key).read_text(encoding="utf-8").strip()

    def _format_items_for_prompt(self, items: list[ContentItem]) -> str:
        blocks = []
        for index, item in enumerate(items, start=1):
            content = item.body if len(item.body) > len(item.summary) else item.summary
            content = content[:2000]
            blocks.append(
                f"--- Item {index} ---\n"
                f"Subject: {item.title}\n"
                f"From: {item.source}\n"
                f"Date: {item.published_at}\n"
                f"Content: {content}"
            )
        return "\n\n".join(blocks)

    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        config = self.config(ctx)
        sections: list[SectionContent] = []
        for section_cfg in config.sections:
            section = ctx.gmail_provider.gather_section(
                section_cfg.name,
                section_cfg.query,
                section_cfg.max_threads,
                config.email_account,
                config.body_max_chars,
            )
            sections.append(section)

        if config.inbox_section and config.inbox_section.enabled:
            inbox = config.inbox_section
            sections.append(
                ctx.gmail_provider.gather_section(
                    inbox.name,
                    inbox.query,
                    inbox.max_threads,
                    config.email_account,
                    config.body_max_chars,
                )
            )

        content = WorkflowContent(sections=sections)
        artifact = ctx.artifact_path("sources.json")
        artifact.write_text(content.model_dump_json(indent=2), encoding="utf-8")
        ctx.artifacts["sources"] = artifact
        return content

    def _estimate_cost(self, config: CitizenBriefWorkflowConfig, input_tokens: int, output_tokens: int) -> float:
        model = config.models[config.model_provider]
        return (model.cost_per_1m_input * input_tokens + model.cost_per_1m_output * output_tokens) / 1_000_000

    def _call_prompt(self, ctx: WorkflowContext, prompt: str) -> tuple[str, int, int, float]:
        config = self.config(ctx)
        response = ctx.llm_provider.complete(prompt, config)
        cost = self._estimate_cost(config, response.input_tokens, response.output_tokens)
        return response.text.strip() or "NO_STRONG_ITEMS", response.input_tokens, response.output_tokens, cost

    def _normalize_summary(self, text: str) -> str:
        normalized = text.strip()
        if normalized in {"NO_STRONG_ITEMS", "- NO_STRONG_ITEMS", "* NO_STRONG_ITEMS"}:
            return "NO_STRONG_ITEMS"
        return normalized

    def _normalize_section_heading(self, text: str) -> str:
        normalized = text.strip()
        if normalized.startswith("**") and normalized.endswith("**") and len(normalized) > 4:
            normalized = normalized[2:-2].strip()
        return normalized

    def _parse_editor_output(self, text: str, section_names: list[str]) -> dict[str, str]:
        parsed: dict[str, str] = {}
        current: str | None = None
        buffer: list[str] = []
        valid_names = set(section_names)
        for line in text.splitlines():
            stripped = self._normalize_section_heading(line)
            if stripped in valid_names:
                if current is not None:
                    parsed[current] = self._normalize_summary("\n".join(buffer))
                current = stripped
                buffer = []
            elif current is not None:
                buffer.append(line)
        if current is not None:
            parsed[current] = self._normalize_summary("\n".join(buffer))
        for name in section_names:
            parsed.setdefault(name, "NO_STRONG_ITEMS")
        return parsed

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        config = self.config(ctx)
        section_prompt = self._read_prompt(ctx, "section")
        inbox_prompt = self._read_prompt(ctx, "inbox")
        editor_prompt = self._read_prompt(ctx, "editor")

        drafted_sections: list[SectionContent] = []
        cost_calls: list[dict[str, float | int | str]] = []

        for section in gathered.sections:
            if not section.items:
                drafted_sections.append(section.model_copy(update={"summary": "NO_STRONG_ITEMS"}))
                continue
            prompt_template = inbox_prompt if config.inbox_section and section.name == config.inbox_section.name else section_prompt
            prompt = prompt_template.format(section=section.name, items=self._format_items_for_prompt(section.items))
            summary, input_tokens, output_tokens, cost = self._call_prompt(ctx, prompt)
            summary = self._normalize_summary(summary)
            cost_calls.append(
                {
                    "section": section.name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": round(cost, 6),
                }
            )
            drafted_sections.append(section.model_copy(update={"summary": summary}))
            safe_name = section.name.replace("/", "_").replace(" ", "_").lower()
            artifact = ctx.artifact_path(f"section_{safe_name}.txt")
            artifact.write_text(summary, encoding="utf-8")
            ctx.artifacts[f"section_{safe_name}"] = artifact

        section_names = [section.name for section in drafted_sections]
        draft_text = "\n\n".join(f"{section.name}\n{section.summary}" for section in drafted_sections)
        headers = "\n".join(f"{name}\n- ..." for name in section_names)
        final_prompt = editor_prompt.format(section_headers=headers, drafts=draft_text)
        final_text, input_tokens, output_tokens, cost = self._call_prompt(ctx, final_prompt)
        cost_calls.append(
            {
                "section": "_editor",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost, 6),
            }
        )
        parsed = self._parse_editor_output(final_text, section_names)

        final_sections = [section.model_copy(update={"summary": parsed[section.name]}) for section in drafted_sections]
        content = WorkflowContent(sections=final_sections)

        summaries_artifact = ctx.artifact_path("summaries.json")
        summaries_artifact.write_text(
            json.dumps({section.name: section.summary for section in final_sections}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx.artifacts["summaries"] = summaries_artifact

        editor_artifact = ctx.artifact_path("final_editor.txt")
        editor_artifact.write_text(final_text, encoding="utf-8")
        ctx.artifacts["editor"] = editor_artifact

        cost_artifact = ctx.artifact_path("cost_report.json")
        cost_artifact.write_text(
            json.dumps(
                {
                    "provider": config.model_provider,
                    "model": config.models[config.model_provider].model,
                    "calls": cost_calls,
                    "total_input_tokens": sum(call["input_tokens"] for call in cost_calls),
                    "total_output_tokens": sum(call["output_tokens"] for call in cost_calls),
                    "total_cost_usd": round(sum(float(call["cost_usd"]) for call in cost_calls), 6),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        ctx.artifacts["cost_report"] = cost_artifact
        return content

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        config = self.config(ctx)
        date_label = datetime.now().strftime("%A, %d %B %Y")
        html_path = resolve_project_path(config.template_html)
        text_path = resolve_project_path(config.template_text)
        subject = config.email_subject
        html = render_digest_html(
            html_path,
            subject=subject,
            heading="Daily Citizen Brief",
            date_label=date_label,
            footer_label="Generated by Email Workflow Platform",
            sections=content.sections,
        )
        text = render_digest_text(
            text_path,
            subject=subject,
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
        return RenderedEmail(subject=subject, html=html, text=text)
