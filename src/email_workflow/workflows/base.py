"""Base workflow abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import RenderedEmail, WorkflowContent, WorkflowMeta, WorkflowResult, WorkflowStatus


class BaseWorkflow(ABC):
    """Base class for workflow implementations."""

    @property
    @abstractmethod
    def workflow_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def meta(self, ctx: WorkflowContext) -> WorkflowMeta:
        raise NotImplementedError

    @abstractmethod
    def gather(self, ctx: WorkflowContext) -> WorkflowContent:
        raise NotImplementedError

    @abstractmethod
    def synthesize(self, ctx: WorkflowContext, gathered: WorkflowContent) -> WorkflowContent:
        raise NotImplementedError

    @abstractmethod
    def render(self, ctx: WorkflowContext, content: WorkflowContent) -> RenderedEmail:
        raise NotImplementedError

    def deliver(self, ctx: WorkflowContext, rendered: RenderedEmail, dry_run: bool) -> None:
        ctx.email_provider.send_email(
            to=self.config(ctx).email_to,
            subject=rendered.subject,
            html_body=rendered.html,
            text_body=rendered.text,
            account=self.config(ctx).email_account,
            dry_run=dry_run,
        )

    @abstractmethod
    def config(self, ctx: WorkflowContext):
        raise NotImplementedError

    def run(self, ctx: WorkflowContext, dry_run: bool = False, skip_delivery: bool = False) -> WorkflowResult:
        result = WorkflowResult(workflow_id=ctx.definition.id, status=WorkflowStatus.RUNNING)
        try:
            gathered = self.gather(ctx)
            synthesized = self.synthesize(ctx, gathered)
            rendered = self.render(ctx, synthesized)
            if not skip_delivery:
                self.deliver(ctx, rendered, dry_run=dry_run)

            result.items_processed = sum(len(section.items) for section in gathered.sections)
            result.output = {
                "run_dir": str(ctx.run_dir),
                "artifacts": {name: str(path) for name, path in ctx.artifacts.items()},
                "subject": rendered.subject,
                "sections": [section.name for section in synthesized.sections],
            }
            result.mark_done(WorkflowStatus.SUCCESS, "Workflow completed successfully.")
        except Exception as exc:
            result.add_error(str(exc))
            result.mark_done(WorkflowStatus.FAILED, str(exc))
        return result
