"""Placeholder weather report workflow."""

from __future__ import annotations

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import RenderedEmail, WorkflowContent, WorkflowMeta
from email_workflow.workflows.base import BaseWorkflow


class WeatherReportWorkflow(BaseWorkflow):
    workflow_type = "weather_report"

    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        return WorkflowMeta(id=ctx.definition.id, name=ctx.definition.name, description=ctx.definition.description)

    def config(self, ctx: WorkflowContext) -> dict:
        return ctx.definition.config

    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        return WorkflowContent()

    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        return gathered

    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        return RenderedEmail(subject=ctx.definition.name, html="<p>Not implemented.</p>", text="Not implemented.")
