"""Простой in-memory rate limiter со скользящим окном.

Хранит метки времени попыток по ключу (например, email или IP). Подходит для
одного процесса; для нескольких воркеров нужен общий стор (Redis). Используется
для защиты логина от перебора (см. configs login_max_attempts/window).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        bucket = self._hits[key]
        threshold = now - self.window_seconds
        while bucket and bucket[0] < threshold:
            bucket.popleft()

    def is_allowed(self, key: str) -> bool:
        """True, если лимит ещё не исчерпан (без регистрации попытки)."""
        with self._lock:
            now = time.monotonic()
            self._prune(key, now)
            return len(self._hits[key]) < self.max_attempts

    def hit(self, key: str) -> None:
        """Регистрирует попытку."""
        with self._lock:
            now = time.monotonic()
            self._prune(key, now)
            self._hits[key].append(now)

    def reset(self, key: str) -> None:
        """Сбрасывает счётчик (например, после успешного входа)."""
        with self._lock:
            self._hits.pop(key, None)


from src.utils.config import settings

# Общий лимитер для попыток входа.
login_limiter = RateLimiter(
    max_attempts=settings.login_max_attempts,
    window_seconds=settings.login_window_seconds,
)
