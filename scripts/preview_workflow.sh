#!/usr/bin/env bash
set -euo pipefail

WORKFLOW_ID="${1:-citizen-brief}"
PYTHONPATH=src python3 -m email_workflow.cli run "$WORKFLOW_ID" --dry-run --skip-delivery
