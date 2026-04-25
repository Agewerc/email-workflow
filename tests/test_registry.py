from email_workflow.engine.registry import WorkflowRegistry
from email_workflow.workflows.surf_report import SurfReportWorkflow


def test_registry_registers_and_creates_workflows() -> None:
    registry = WorkflowRegistry()
    registry.register("surf_report", SurfReportWorkflow)
    workflow = registry.create("surf_report")
    assert workflow.workflow_type == "surf_report"
