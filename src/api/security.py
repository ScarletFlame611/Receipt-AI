"""Примитивы безопасности: хеширование паролей, JWT, проверка ролей.

Здесь нет работы с БД и зависимостей FastAPI — только чистые функции,
которые удобно тестировать и переиспользовать. Связка с запросом живёт
в src/api/dependencies.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.utils.config import settings

# --------------------------------------------------------------------------
# Пароли
# --------------------------------------------------------------------------
# Поддерживаем обе схемы: argon2 (по умолчанию) и bcrypt. Хешируем выбранной
# в конфиге схемой, а проверять умеем любую — это позволяет менять схему без
# инвалидации старых хешей. deprecated="auto" помечает устаревшие хеши, чтобы
# при следующем успешном логине их можно было перехешировать.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    default=settings.password_hash_scheme,
)


def hash_password(password: str) -> str:
    """Возвращает хеш пароля выбранной в конфиге схемой."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Безопасно сверяет пароль с хешем. Никогда не бросает на «битом» хеше."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True, если хеш сделан устаревшей схемой и стоит перехешировать."""
    return pwd_context.needs_update(password_hash)


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------
def create_access_token(
    subject: str | int,
    *,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Создаёт подписанный access-токен.

    subject попадает в клейм ``sub`` (обычно id пользователя). Время жизни —
    из конфига, если не передано явно. ``extra_claims`` позволяет положить,
    например, флаг роли, но источником истины для прав остаётся БД.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Проверяет подпись и срок действия токена.

    Возвращает payload при успехе, ``None`` — если токен невалиден, просрочен
    или подделан. Ошибки наружу не пробрасываем, решение принимает вызывающий.
    """
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
