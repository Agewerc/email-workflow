"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[3]


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a repository-relative or absolute path."""

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
