"""Email delivery via the gog Gmail CLI."""

from __future__ import annotations

import logging
import subprocess

from .base import EmailProvider

logger = logging.getLogger(__name__)


class GogEmailProvider(EmailProvider):
    """Send email with `gog gmail send`."""

    def run_cmd(self, cmd: list[str]) -> tuple[str, str, int]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        account: str,
        dry_run: bool = False,
    ) -> bool:
        if dry_run:
            logger.info("[dry-run] would send to=%s subject=%r", to, subject)
            return True

        html_cmd = [
            "gog",
            "gmail",
            "send",
            "--to",
            to,
            "--subject",
            subject,
            "--body-html",
            html_body,
            "--account",
            account,
            "--no-input",
        ]
        stdout, stderr, code = self.run_cmd(html_cmd)
        if code == 0:
            logger.info("HTML email sent: %s", stdout.strip()[:200])
            return True

        logger.warning("HTML send failed: %s", stderr.strip()[:200])
        text_cmd = [
            "gog",
            "gmail",
            "send",
            "--to",
            to,
            "--subject",
            subject,
            "--body",
            text_body,
            "--account",
            account,
            "--no-input",
        ]
        stdout, stderr, code = self.run_cmd(text_cmd)
        if code == 0:
            logger.info("Plain text email sent: %s", stdout.strip()[:200])
            return True
        raise RuntimeError(f"Failed to send email: {stderr.strip()[:200]}")
