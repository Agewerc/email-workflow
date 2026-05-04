"""Public schema exports for the email workflow platform."""

from .config import (
    AppSettings,
    BeachConfig,
    CitizenBriefWorkflowConfig,
    InboxSectionConfig,
    JobAlertDigestWorkflowConfig,
    LLMModelConfig,
    ProfGInsightsWorkflowConfig,
    WeekendWeatherSurfWorkflowConfig,
    SectionQueryConfig,
    WorkflowCatalog,
    WorkflowDefinition,
    load_workflow_catalog,
)
from .content import ContentItem, InsightItem, JobOpportunity, SectionContent, WorkflowContent
from .weather_surf import ForecastPeriodStats, SurfSlotForecast, WeekendDayForecast, WeekendForecast
from .workflow import RenderedEmail, WorkflowMeta, WorkflowResult, WorkflowStatus

__all__ = [
    "AppSettings",
    "BeachConfig",
    "CitizenBriefWorkflowConfig",
    "ContentItem",
    "ForecastPeriodStats",
    "InboxSectionConfig",
    "InsightItem",
    "JobAlertDigestWorkflowConfig",
    "JobOpportunity",
    "LLMModelConfig",
    "ProfGInsightsWorkflowConfig",
    "RenderedEmail",
    "SectionContent",
    "SectionQueryConfig",
    "SurfSlotForecast",
    "WeekendDayForecast",
    "WeekendForecast",
    "WeekendWeatherSurfWorkflowConfig",
    "WorkflowCatalog",
    "WorkflowContent",
    "WorkflowDefinition",
    "WorkflowMeta",
    "WorkflowResult",
    "WorkflowStatus",
    "load_workflow_catalog",
]
