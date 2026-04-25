"""Gmail content provider backed by the `gog` CLI."""

from __future__ import annotations

import base64
import json
import logging
import re
import subprocess

from email_workflow.schemas import ContentItem, SectionContent

logger = logging.getLogger(__name__)


class GmailContentProvider:
    """Fetch email threads via the gog Gmail CLI."""

    def run_cmd(self, cmd: list[str]) -> tuple[str, str, int]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode

    def strip_html(self, raw: str) -> str:
        text = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.S | re.I)
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"&[a-z]+;", "", text)
        return re.sub(r"\s{2,}", " ", text).strip()

    def decode_b64(self, data: str) -> str:
        padded = data + "=" * (-len(data) % 4)
        try:
            return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def extract_body(self, payload: dict) -> str:
        mime = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data", "")
        if mime == "text/plain" and body_data:
            return self.decode_b64(body_data)
        if mime == "text/html" and body_data:
            return self.strip_html(self.decode_b64(body_data))

        plain = ""
        html = ""
        for part in payload.get("parts", []):
            part_mime = part.get("mimeType", "")
            if part_mime == "text/plain":
                plain = self.extract_body(part)
            elif part_mime == "text/html":
                html = self.extract_body(part)
            elif part_mime.startswith("multipart/"):
                nested = self.extract_body(part)
                if nested:
                    plain = nested
        return plain or html

    def gmail_search(self, query: str, max_results: int, account: str) -> list[dict]:
        cmd = [
            "gog",
            "gmail",
            "search",
            query,
            "--account",
            account,
            "--max",
            str(max_results),
            "--json",
            "--no-input",
        ]
        stdout, stderr, code = self.run_cmd(cmd)
        if code != 0:
            logger.warning("gmail_search failed for %r: %s", query, stderr.strip()[:200])
            return []
        try:
            data = json.loads(stdout or "{}")
            return data.get("threads") or []
        except json.JSONDecodeError:
            logger.warning("gmail_search parse error for %r", query)
            return []

    def gmail_thread_detail(self, thread_id: str, account: str) -> ContentItem | None:
        cmd = [
            "gog",
            "gmail",
            "thread",
            "get",
            thread_id,
            "--account",
            account,
            "--json",
            "--no-input",
        ]
        stdout, stderr, code = self.run_cmd(cmd)
        if code != 0:
            logger.warning("thread_get failed for %s: %s", thread_id, stderr.strip()[:200])
            return None
        try:
            data = json.loads(stdout or "{}")
        except json.JSONDecodeError:
            logger.warning("thread_get parse error for %s", thread_id)
            return None

        messages = data.get("thread", {}).get("messages", [])
        if not messages:
            return None

        message = messages[-1]
        payload = message.get("payload", {})
        headers = {header.get("name", "").lower(): header.get("value", "") for header in payload.get("headers", [])}
        return ContentItem(
            identifier=thread_id,
            title=headers.get("subject", "(no subject)"),
            source=headers.get("from", ""),
            published_at=headers.get("date", ""),
            summary=message.get("snippet", ""),
            body=self.extract_body(payload),
            metadata={"thread_id": thread_id},
        )

    def gather_section(self, name: str, query: str, max_threads: int, account: str, body_max_chars: int) -> SectionContent:
        items: list[ContentItem] = []
        threads = self.gmail_search(query, max_threads, account)
        for thread in threads:
            thread_id = thread.get("id")
            if not thread_id:
                continue
            detail = self.gmail_thread_detail(thread_id, account)
            if detail is None:
                continue
            detail.body = detail.body[:body_max_chars]
            detail.summary = detail.summary[:300]
            items.append(detail)
        return SectionContent(name=name, items=items)
