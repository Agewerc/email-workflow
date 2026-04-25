"""Reusable workflow content schemas."""

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A normalized content unit gathered for a workflow section."""

    identifier: str
    title: str
    source: str = ""
    published_at: str = ""
    summary: str = ""
    body: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class SectionContent(BaseModel):
    """Content grouped under a named section."""

    name: str
    items: list[ContentItem] = Field(default_factory=list)
    summary: str = "NO_STRONG_ITEMS"


class WorkflowContent(BaseModel):
    """All gathered and synthesized content for a workflow run."""

    sections: list[SectionContent] = Field(default_factory=list)

