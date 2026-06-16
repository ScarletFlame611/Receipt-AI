"""Зависимости FastAPI
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Не удалось проверить учётные данные",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Annotated[Session, Depends(get_db)],
) -> User:
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
_pipeline = None
_pipeline_lock = threading.Lock()


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                from src.models.pipeline import ReceiptPipeline
                logger.info("Загрузка ML-пайплайна (один раз на процесс)...")
                _pipeline = ReceiptPipeline()
                logger.info("ML-пайплайн загружен.")
    return _pipeline


def warmup_pipeline() -> None:
    get_pipeline()


def is_pipeline_loaded() -> bool:
    return _pipeline is not None


def pipeline_components() -> dict[str, bool]:
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
