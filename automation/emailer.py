"""Email alert dispatcher."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, Iterable


def _default_smtp_factory(host: str, port: int) -> smtplib.SMTP:
    return smtplib.SMTP(host, port)


@dataclass
class EmailConfig:
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    recipient: str
    use_tls: bool = True


class EmailDispatcher:
    """Sends email alerts using provided configuration."""

    def __init__(self, config: EmailConfig, smtp_factory: Callable[[str, int], smtplib.SMTP] = _default_smtp_factory) -> None:
        self.config = config
        self.smtp_factory = smtp_factory

    def send_alert(self, subject: str, body: str) -> None:
        message = self._build_message(subject, body)
        with self.smtp_factory(self.config.smtp_server, self.config.smtp_port) as smtp:
            if self.config.use_tls:
                smtp.starttls()
            smtp.login(self.config.username, self.config.password)
            smtp.send_message(message)

    def _build_message(self, subject: str, body: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = self.config.username
        msg["To"] = self.config.recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        return msg


__all__ = ["EmailDispatcher", "EmailConfig"]
