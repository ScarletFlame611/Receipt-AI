"""Единый логгер проекта. Никогда не логирует пароли и токены."""
from __future__ import annotations

import logging
import re
import sys

_SENSITIVE = re.compile(
    r"(password|passwd|token|secret|authorization|jwt)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


class RedactFilter(logging.Filter):
    """Маскирует чувствительные значения в сообщениях логов."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE.sub(r"\1=***", record.msg)
        return True


_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RedactFilter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Возвращает именованный логгер (вызывает setup_logging при первом обращении)."""
    setup_logging()
    return logging.getLogger(name)