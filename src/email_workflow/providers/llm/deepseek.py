"""DeepSeek provider using the OpenAI-compatible API shape."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Alias provider for DeepSeek-backed chat completions."""
