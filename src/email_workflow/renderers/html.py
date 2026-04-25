"""HTML renderer helpers."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from email_workflow.schemas import SectionContent

SECTION_ICONS = {
    "News": "📰",
    "Economics": "📈",
    "Brazil": "🇧🇷",
    "Tech/AI": "🤖",
    "Prof G Insights": "🎙️",
    "Inbox Highlights": "📬",
}


def render_digest_html(
    template_path: Path,
    *,
    subject: str,
    heading: str,
    date_label: str,
    footer_label: str,
    sections: list[SectionContent],
) -> str:
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    return template.render(
        subject=subject,
        heading=heading,
        date_label=date_label,
        footer_label=footer_label,
        sections=sections,
        section_icons=SECTION_ICONS,
    )
