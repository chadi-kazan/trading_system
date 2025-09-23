from __future__ import annotations

from unittest.mock import MagicMock

from automation.emailer import EmailConfig, EmailDispatcher


def _dispatcher_with_mock():
    config = EmailConfig(
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="user@example.com",
        password="password",
        recipient="alerts@example.com",
    )
    smtp_cm = MagicMock()
    smtp_instance = MagicMock()
    smtp_cm.__enter__.return_value = smtp_instance
    smtp_factory = MagicMock(return_value=smtp_cm)
    dispatcher = EmailDispatcher(config, smtp_factory=smtp_factory)
    return dispatcher, smtp_factory, smtp_instance


def test_email_dispatcher_sends_message():
    dispatcher, smtp_factory, smtp_instance = _dispatcher_with_mock()

    dispatcher.send_alert("Subject", "Body")

    smtp_factory.assert_called_once_with("smtp.example.com", 587)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user@example.com", "password")
    smtp_instance.send_message.assert_called_once()


def test_build_message_sets_headers():
    dispatcher, _, _ = _dispatcher_with_mock()
    msg = dispatcher._build_message("Sub", "Body")

    assert msg["From"] == "user@example.com"
    assert msg["To"] == "alerts@example.com"
    assert msg["Subject"] == "Sub"
