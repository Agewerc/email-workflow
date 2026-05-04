"""Configuration models and file-backed workflow definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Top-level application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    email_account: str = "alangewerc@gmail.com"
    webapp_host: str = "127.0.0.1"
    webapp_port: int = 8000
    webapp_reload: bool = True
    log_level: str = "INFO"
    default_workflow_file: str = "config/workflows.yaml"
    default_prompt_dir: str = "config/prompts"
    run_dir: str = "runs"
    log_dir: str = "logs"


class LLMModelConfig(BaseModel):
    api_key_env: str | None = None
    base_url: str | None = None
    model: str
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0


class SectionQueryConfig(BaseModel):
    name: str
    query: str
    max_threads: int = 5


class InboxSectionConfig(SectionQueryConfig):
    enabled: bool = False


class CitizenBriefWorkflowConfig(BaseModel):
    workflow_type: Literal["citizen_brief"] = "citizen_brief"
    email_account: str = "alangewerc@gmail.com"
    email_to: str
    email_subject: str = "Daily Citizen Brief"
    model_provider: str = "deepseek"
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)
    sections: list[SectionQueryConfig] = Field(default_factory=list)
    inbox_section: InboxSectionConfig | None = None
    body_max_chars: int = 2500
    llm_retries: int = 2
    llm_timeout_seconds: int = 30
    prompt_files: dict[str, str] = Field(default_factory=dict)
    template_html: str = "templates/digest.html.j2"
    template_text: str = "templates/digest.txt.j2"


class JobAlertDigestWorkflowConfig(BaseModel):
    workflow_type: Literal["job_alert_digest", "job_alert_whole_pool_experiment"] = "job_alert_digest"
    email_account: str = "alangewerc@gmail.com"
    email_to: str
    email_subject: str = "Job Alert Digest"
    model_provider: str = "deepseek"
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)
    gmail_query: str = 'label:"Jobs" newer_than:1d'
    max_threads: int = 25
    body_max_chars: int = 6000
    max_jobs_per_email: int = 6
    max_digest_jobs: int = 12
    min_digest_score: int = 55
    profile_file: str = "config/profile/alan_job_profile.md"
    inclusion_keywords: list[str] = Field(default_factory=list)
    exclusion_keywords: list[str] = Field(default_factory=list)
    target_functions: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    seniority_keywords: list[str] = Field(default_factory=list)
    prompt_files: dict[str, str] = Field(default_factory=dict)
    llm_score_fallback_to_rules: bool = True
    llm_timeout_seconds: int = 30
    template_html: str = "src/email_workflow/templates/job_alert_digest.html.j2"
    template_text: str = "src/email_workflow/templates/job_alert_digest.txt.j2"


class ProfGInsightsWorkflowConfig(BaseModel):
    workflow_type: Literal["prof_g_insights"] = "prof_g_insights"
    email_account: str = "alangewerc@gmail.com"
    email_to: str
    email_subject: str = "Weekly Prof G Insights"
    model_provider: str = "deepseek"
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)
    gmail_query: str = "label:newsletter-prof-g newer_than:7d"
    max_threads: int = 12
    body_max_chars: int = 8000
    max_insights: int = 5
    llm_timeout_seconds: int = 60
    llm_max_tokens: int = 3200
    prompt_files: dict[str, str] = Field(default_factory=dict)
    template_html: str = "src/email_workflow/templates/digest.html.j2"
    template_text: str = "src/email_workflow/templates/digest.txt.j2"


class BeachConfig(BaseModel):
    slug: str
    name: str
    latitude: float
    longitude: float
    surfline_spot_id: str | None = None


class WeekendWeatherSurfWorkflowConfig(BaseModel):
    workflow_type: Literal["weekend_weather_surf"] = "weekend_weather_surf"
    email_account: str = "alangewerc@gmail.com"
    email_to: str
    email_subject: str = "Weekend Weather + Surf Forecast"
    beach: BeachConfig
    timezone: str = "Australia/Perth"
    forecast_days: int = 8
    schedule_day: str = "Thursday"
    schedule_time: str = "18:00"
    schedule_timezone: str = "Australia/Perth"
    weather_source_label: str = "Open-Meteo"
    surf_source_label: str = "Surfline"
    template_html: str = "src/email_workflow/templates/weekend_weather_surf.html.j2"
    template_text: str = "src/email_workflow/templates/weekend_weather_surf.txt.j2"


class WorkflowDefinition(BaseModel):
    id: str
    workflow_type: str
    enabled: bool = True
    frequency: str = "2026-01-01T09:00:00+08:00"
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowCatalog(BaseModel):
    workflows: list[WorkflowDefinition] = Field(default_factory=list)

    def get(self, workflow_id: str) -> WorkflowDefinition:
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow
        raise KeyError(f"Unknown workflow: {workflow_id}")


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_workflow_catalog(path: Path) -> WorkflowCatalog:
    """Load workflow definitions from YAML."""

    payload = load_yaml(path)
    return WorkflowCatalog.model_validate(payload)
