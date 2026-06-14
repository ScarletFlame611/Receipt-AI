"""Зависимости FastAPI: сессия БД, текущий пользователь, проверка ролей
и единый экземпляр тяжёлого ML-пайплайна.

Ключевой момент — пайплайн (детектор + OCR + NER + категоризатор) грузится
ОДИН раз на процесс, а не на каждый запрос. Загрузка моделей дорогая по
времени и памяти, поэтому держим ровно один экземпляр (см. get_pipeline).
"""
from __future__ import annotations

import threading
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.api.security import decode_access_token
from src.db import crud
from src.db.base import get_db
from src.db.models import User
from src.utils.logging import get_logger

logger = get_logger(__name__)

# tokenUrl указывает на роут логина — Swagger UI использует его для формы.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Не удалось проверить учётные данные",
    headers={"WWW-Authenticate": "Bearer"},
)


# --------------------------------------------------------------------------
# Пользователь и роли
# --------------------------------------------------------------------------
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Достаёт пользователя из JWT.

    401, если токен невалиден/просрочен, в нём нет ``sub`` или пользователь
    не найден. 403, если аккаунт деактивирован.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise _CREDENTIALS_EXC

    sub = payload.get("sub")
    if sub is None:
        raise _CREDENTIALS_EXC
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise _CREDENTIALS_EXC

    user = crud.get_user(db, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись отключена",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    """Пропускает только администратора, иначе 403."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


# --------------------------------------------------------------------------
# ML-пайплайн: один экземпляр на процесс
# --------------------------------------------------------------------------
_pipeline = None
_pipeline_lock = threading.Lock()


def get_pipeline():
    """Возвращает единственный экземпляр ReceiptPipeline (ленивая загрузка).

    Двойная проверка под блокировкой защищает от гонки, если несколько
    запросов одновременно дёрнут пайплайн до прогрева. После первого вызова
    модели уже в памяти — последующие запросы получают готовый объект.
    """
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                # Импорт внутри функции, чтобы тяжёлые ML-зависимости не
                # тянулись при импорте модуля (важно для тестов и старта без
                # инференса).
                from src.models.pipeline import ReceiptPipeline

                logger.info("Загрузка ML-пайплайна (один раз на процесс)...")
                _pipeline = ReceiptPipeline()
                logger.info("ML-пайплайн загружен.")
    return _pipeline


def warmup_pipeline() -> None:
    """Прогрев на старте приложения — чтобы первый запрос не ждал модели.

    Вызывать из lifespan/startup. Идемпотентно: повторный вызов вернёт уже
    загруженный экземпляр.
    """
    get_pipeline()


def is_pipeline_loaded() -> bool:
    """True, если пайплайн уже создан. Не инициирует загрузку (для health-check)."""
    return _pipeline is not None


def pipeline_components() -> dict[str, bool]:
    """Состав загруженного пайплайна для диагностики в health-check.

    Не трогает синглтон (не грузит модели), просто отражает текущее состояние.
    """
    if _pipeline is None:
        return {}
    return {
        "detector": getattr(_pipeline, "detector", None) is not None,
        "ocr": getattr(_pipeline, "ocr", None) is not None,
        "ner": getattr(_pipeline, "ner", None) is not None,
        "brand_matcher": getattr(_pipeline, "brand_matcher", None) is not None,
        "categorizer": getattr(_pipeline, "categorizer", None) is not None,
    }


Pipeline = Annotated[object, Depends(get_pipeline)]
