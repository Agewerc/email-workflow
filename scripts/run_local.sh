#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m email_workflow.cli run citizen-brief --dry-run --skip-delivery
