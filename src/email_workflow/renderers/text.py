"""Plain text renderer helpers."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from email_workflow.schemas import SectionContent


def render_digest_text(
    template_path: Path,
    *,
    subject: str,
    date_label: str,
    footer_label: str,
    sections: list[SectionContent],
) -> str:
    env = Environment(loader=FileSystemLoader(template_path.parent), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template_path.name)
    return template.render(
        subject=subject,
        date_label=date_label,
        footer_label=footer_label,
        sections=sections,
    )
