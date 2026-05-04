"""HTML renderer helpers."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from email_workflow.schemas import SectionContent

SECTION_ICONS = {
    "News": "📰",
    "Economics": "📈",
    "Australia": "🇦🇺",
    "Brazil": "🇧🇷",
    "Tech/AI": "🤖",
    "Prof G Insights": "🎙️",
    "Inbox Highlights": "📬",
}


INLINE_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
INLINE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
INLINE_LINK_LABEL_PATTERN = re.compile(r"(Link:\s*)(https?://[^\s<]+)")
LINK_LINE_URL_PATTERN = re.compile(r"^Link:\s*(https?://\S+)\s*$")
RAW_URL_LINE_PATTERN = re.compile(r"^(https?://\S+)\s*$")
MARKDOWN_LINK_ONLY_PATTERN = re.compile(r"^\[([^\]]+)\]\((https?://[^\s)]+)\)\s*$")
LEADING_BOLD_PATTERN = re.compile(r"^\*\*(.+?)\*\*(.*)$")


def render_inline_markdown(text: str) -> Markup:
    escaped = escape(text)
    rendered = str(escaped)
    rendered = INLINE_LINK_PATTERN.sub(
        r'<a href="\2" style="color:#087e8b;text-decoration:underline;">\1</a>',
        rendered,
    )
    rendered = INLINE_LINK_LABEL_PATTERN.sub(
        r'\1<a href="\2" style="color:#087e8b;text-decoration:underline;">\2</a>',
        rendered,
    )
    rendered = INLINE_BOLD_PATTERN.sub(r"<strong>\1</strong>", rendered)
    return Markup(rendered)


def _render_title_linked_line(text: str, url: str) -> Markup:
    match = LEADING_BOLD_PATTERN.match(text.strip())
    escaped_url = escape(url)
    if not match:
        return render_inline_markdown(f"[Open role]({url}) {text}")
    title = escape(match.group(1))
    remainder = render_inline_markdown(match.group(2).strip())
    anchor = Markup(
        f'<a href="{escaped_url}" style="color:#087e8b;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:2px;font-weight:700;">'
        f'<strong>{title}</strong> <span style="font-weight:700;">↗</span>'
        f"</a>"
    )
    if str(remainder):
        return Markup(f"{anchor} {remainder}")
    return anchor


def _extract_inline_link(text: str) -> tuple[str, str | None]:
    match = INLINE_LINK_PATTERN.search(text)
    if not match:
        return text, None
    cleaned = INLINE_LINK_PATTERN.sub("", text, count=1).strip()
    return cleaned, match.group(2)


def render_summary_html(summary: str) -> Markup:
    blocks: list[str] = []
    for raw_block in re.split(r"\n\s*\n", summary.strip()):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if not lines:
            continue
        link_url: str | None = None
        content_lines: list[str] = []
        for line in lines:
            link_match = LINK_LINE_URL_PATTERN.match(line)
            if link_match:
                link_url = link_match.group(1)
            elif MARKDOWN_LINK_ONLY_PATTERN.match(line):
                link_url = MARKDOWN_LINK_ONLY_PATTERN.match(line).group(2)
            elif RAW_URL_LINE_PATTERN.match(line):
                link_url = RAW_URL_LINE_PATTERN.match(line).group(1)
            else:
                content_lines.append(line)

        for index, line in enumerate(content_lines):
            cleaned_line, inline_link_url = _extract_inline_link(line)
            effective_link = link_url if index == 0 and link_url else inline_link_url
            if effective_link and LEADING_BOLD_PATTERN.match(cleaned_line):
                rendered = _render_title_linked_line(cleaned_line, effective_link)
            else:
                rendered = render_inline_markdown(line)
            blocks.append(
                f'<p style="margin:0 0 10px;font-size:14px;line-height:1.65;color:#314452;">{rendered}</p>'
            )
    return Markup("\n".join(blocks))


def render_html_template(template_path: Path, **context: Any) -> str:
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["inline_markdown"] = render_inline_markdown
    env.filters["summary_html"] = render_summary_html
    template = env.get_template(template_path.name)
    return template.render(**context)


def render_digest_html(
    template_path: Path,
    *,
    subject: str,
    heading: str,
    date_label: str,
    footer_label: str,
    sections: list[SectionContent],
) -> str:
    return render_html_template(
        template_path,
        subject=subject,
        heading=heading,
        date_label=date_label,
        footer_label=footer_label,
        sections=sections,
        section_icons=SECTION_ICONS,
    )
