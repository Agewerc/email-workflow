"""OpenAI-compatible LLM provider."""

from __future__ import annotations

import os

import httpx

from email_workflow.schemas import CitizenBriefWorkflowConfig

from .base import LLMProvider, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    """Call OpenAI-compatible chat completion APIs."""

    def complete(self, prompt: str, config: CitizenBriefWorkflowConfig) -> LLMResponse:
        model_cfg = config.models[config.model_provider]
        if not model_cfg.api_key_env:
            raise RuntimeError(f"Provider {config.model_provider} requires an api_key_env value.")
        api_key = os.environ.get(model_cfg.api_key_env, "")
        if not api_key:
            raise RuntimeError(f"API key not set for {config.model_provider}: export {model_cfg.api_key_env}")
        if not model_cfg.base_url:
            raise RuntimeError(f"Provider {config.model_provider} requires base_url.")

        payload = {
            "model": model_cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 700,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        url = model_cfg.base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=config.llm_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        return LLMResponse(
            text=data["choices"][0]["message"]["content"].strip(),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
