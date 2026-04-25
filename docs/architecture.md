# Architecture

The platform is organized around four layers:

1. Engine: registry, runner, context, and execution lifecycle.
2. Workflows: business logic for a specific briefing or report.
3. Providers and renderers: Gmail, LLM, delivery, and output generation.
4. File-backed assets: YAML workflow definitions, prompt files, templates, and docs.

Citizen Brief is the reference workflow and proves the gather -> synthesize -> render -> deliver shape.
