"""Reusable workflow content schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A normalized content unit gathered for a workflow section."""

    identifier: str
    title: str
    source: str = ""
    published_at: str = ""
    summary: str = ""
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobOpportunity(BaseModel):
    """A normalized job opportunity extracted from one or more emails."""

    title: str
    company: str = ""
    location: str = ""
    link: str = ""
    summary: str = ""
    source_email: str = ""
    relevance_reason: str = ""
    score: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class InsightItem(BaseModel):
    """A synthesized strategic insight backed by source emails."""

    title: str
    conclusion: str
    supporting_data_evidence: str
    considerations_watch_next: str
    source_emails: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SectionContent(BaseModel):
    """Content grouped under a named section."""

    name: str
    items: list[ContentItem] = Field(default_factory=list)
    summary: str = "NO_STRONG_ITEMS"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowContent(BaseModel):
    """All gathered and synthesized content for a workflow run."""

    sections: list[SectionContent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
