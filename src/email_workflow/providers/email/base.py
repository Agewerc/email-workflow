"""Email provider interface."""

from __future__ import annotations


class EmailProvider:
    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        account: str,
        dry_run: bool = False,
    ) -> bool:
        raise NotImplementedError
