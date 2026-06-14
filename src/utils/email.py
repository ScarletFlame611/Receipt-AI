"""Отправка писем. Два бэкенда: console (по умолчанию, печатает в лог) и smtp.

В dev/тестах письмо просто пишется в лог — внешний SMTP не нужен. Тело письма
не содержит пароля, только одноразовый токен сброса.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Отправляет письмо выбранным в конфиге бэкендом."""
    if settings.email_backend == "smtp" and settings.smtp_host:
        _send_smtp(to, subject, body)
    else:
        logger.info("[email:console] to=%s | %s\n%s", to, subject, body)


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    logger.info("Письмо отправлено через SMTP на %s", to)


def send_password_reset(to: str, token: str) -> None:
    """Письмо со ссылкой/токеном сброса пароля."""
    body = (
        "Вы запросили сброс пароля в Receipt-AI.\n\n"
        f"Токен для сброса: {token}\n\n"
        "Если это были не вы — просто проигнорируйте письмо."
    )
    send_email(to, "Receipt-AI: сброс пароля", body)
