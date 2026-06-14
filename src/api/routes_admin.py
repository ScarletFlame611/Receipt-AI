"""Роуты администратора: список пользователей, блокировка, метрики системы.

Весь роутер защищён require_admin — доступ только пользователям с is_admin.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import AdminUser, get_db, require_admin
from src.db import crud, schemas

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],  # гейт на весь роутер
)


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 100,
    offset: int = 0,
):
    return crud.list_users(db, limit=limit, offset=offset)


@router.post("/users/{user_id}/block", response_model=schemas.UserOut)
def block_user(
    user_id: int,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя заблокировать самого себя")
    user = crud.set_user_active(db, user_id, is_active=False)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user


@router.post("/users/{user_id}/unblock", response_model=schemas.UserOut)
def unblock_user(
    user_id: int,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    user = crud.set_user_active(db, user_id, is_active=True)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user


@router.get("/metrics", response_model=schemas.SystemMetrics)
def metrics(admin: AdminUser, db: Annotated[Session, Depends(get_db)]):
    return crud.system_metrics(db)
