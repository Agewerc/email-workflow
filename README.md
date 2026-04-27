# Email Workflow Platform

Email Workflow Platform is a modular, config-driven foundation for automated email briefings. It promotes workflows, prompts, renderers, and providers to first-class assets instead of burying behavior inside one-off scripts.

The first concrete workflow in this repo is **Citizen Brief**, a daily email that gathers newsletter and inbox signals from Gmail, synthesizes them with an LLM, renders HTML/text output, and optionally sends the result back through Gmail.

## Current scope

- `CitizenBriefWorkflow` as the first fully wired workflow
- `WeekendWeatherSurfWorkflow` for reusable beach-based weekend surf/weather outlooks
- file-backed workflow catalog in `config/workflows.example.yaml`
- prompt assets in `config/prompts/`
- reusable providers for Gmail content, LLM access, and Gmail delivery
- reusable HTML/text rendering templates
- CLI for listing and running workflows
- lightweight FastAPI admin UI for inspecting workflows and editing prompt files

## Quick start

```bash
cd /Users/alangewerc/Library/CloudStorage/GoogleDrive-alangewerc@gmail.com/My\ Drive/AI\ \&\ Data\ Projects/email-workflows
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

The runner looks for `config/workflows.yaml` first and falls back to `config/workflows.example.yaml`.

## CLI

```bash
email-workflow list-workflows
email-workflow run citizen-brief --dry-run --skip-delivery
email-workflow web --host 127.0.0.1 --port 8000
```

## Project layout

- `src/email_workflow/engine/`: registry, runner, context
- `src/email_workflow/workflows/`: workflow implementations
- `src/email_workflow/providers/`: external-system adapters
- `src/email_workflow/renderers/`: shared rendering helpers
- `config/`: workflow definitions and prompt files
- `src/email_workflow/webapp/`: internal admin UI
- `tests/`: runner, registry, workflow, and webapp coverage

## Notes

- Gmail access depends on the `gog` CLI being installed and authenticated.
- The default LLM provider is DeepSeek through an OpenAI-compatible API interface.
- Run artifacts are written to `runs/<workflow-id>/<timestamp>/`.
