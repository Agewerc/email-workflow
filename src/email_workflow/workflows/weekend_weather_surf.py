"""Weekend weather + surf workflow."""

from __future__ import annotations

import json

from email_workflow.engine.context import WorkflowContext
from email_workflow.renderers.html import render_html_template
from email_workflow.renderers.text import render_text_template
from email_workflow.schemas import (
    ContentItem,
    RenderedEmail,
    SectionContent,
    WeekendForecast,
    WeekendWeatherSurfWorkflowConfig,
    WorkflowContent,
    WorkflowMeta,
)
from email_workflow.utils.files import resolve_project_path
from email_workflow.workflows.base import BaseWorkflow


class WeekendWeatherSurfWorkflow(BaseWorkflow):
    workflow_type = "weekend_weather_surf"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(
            id=ctx.definition.id,
            name=ctx.definition.name,
            description=ctx.definition.description,
            tags=ctx.definition.tags,
        )

    def config(self, ctx: WorkflowContext) -> WeekendWeatherSurfWorkflowConfig:
        return WeekendWeatherSurfWorkflowConfig.model_validate({"workflow_type": self.workflow_type, **ctx.definition.config})

    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        config = self.config(ctx)
        forecast = ctx.weekend_forecast_provider.fetch_forecast(config)
        sections = [
            SectionContent(
                name="Weekend Outlook",
                summary="\n".join(f"- {line}" for line in forecast.summary),
                items=[
                    ContentItem(
                        identifier="overview",
                        title=forecast.headline,
                        summary=forecast.practical_note,
                        metadata={"best_day": forecast.best_day, "best_window": forecast.best_window},
                    )
                ],
            )
        ]
        for day in forecast.days:
            sections.append(
                SectionContent(
                    name=day.label,
                    summary=day.practical_note,
                    items=[
                        ContentItem(
                            identifier=day.iso_date,
                            title=day.label,
                            summary=day.weather_desc,
                            metadata=day.model_dump(mode="json"),
                        )
                    ],
                )
            )

        content = WorkflowContent(sections=sections, metadata={"forecast": forecast.model_dump(mode="json")})
        artifact = ctx.artifact_path("forecast.json")
        artifact.write_text(json.dumps(forecast.model_dump(mode="json"), indent=2), encoding="utf-8")
        ctx.artifacts["forecast"] = artifact
        return content

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        forecast = WeekendForecast.model_validate(gathered.metadata["forecast"])
        summary_artifact = ctx.artifact_path("summary.json")
        summary_artifact.write_text(
            json.dumps(
                {
                    "headline": forecast.headline,
                    "best_day": forecast.best_day,
                    "best_window": forecast.best_window,
                    "summary": forecast.summary,
                    "practical_note": forecast.practical_note,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        ctx.artifacts["summary"] = summary_artifact
        return gathered

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        config = self.config(ctx)
        forecast = WeekendForecast.model_validate(content.metadata["forecast"])
        html = render_html_template(
            resolve_project_path(config.template_html),
            subject=config.email_subject,
            forecast=forecast,
        )
        text = render_text_template(
            resolve_project_path(config.template_text),
            subject=config.email_subject,
            forecast=forecast,
        )
        html_artifact = ctx.artifact_path("email.html")
        html_artifact.write_text(html, encoding="utf-8")
        text_artifact = ctx.artifact_path("email.txt")
        text_artifact.write_text(text, encoding="utf-8")
        ctx.artifacts["email_html"] = html_artifact
        ctx.artifacts["email_text"] = text_artifact
        return RenderedEmail(subject=config.email_subject, html=html, text=text)
