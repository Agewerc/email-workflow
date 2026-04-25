"""Logging helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from .files import ensure_directory


def configure_logging(level: str, log_dir: Path | None = None) -> None:
    """Configure root logging once."""

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_dir is not None:
        ensure_directory(log_dir)
        handlers.append(logging.FileHandler(log_dir / "email-workflow.log", encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
