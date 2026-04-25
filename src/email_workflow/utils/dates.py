"""Date helpers used across the platform."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_slug() -> str:
    return utc_now().strftime("%Y%m%d-%H%M%S")
