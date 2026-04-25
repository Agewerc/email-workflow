"""LLM provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass

from email_workflow.schemas import CitizenBriefWorkflowConfig


@dataclass(slots=True)
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider:
    """Base interface for text generation providers."""

    def complete(self, prompt: str, config: CitizenBriefWorkflowConfig) -> LLMResponse:
        raise NotImplementedError
