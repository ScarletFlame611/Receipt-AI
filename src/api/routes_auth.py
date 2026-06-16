"""Роуты аутентификации"""
from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.api.dependencies import CurrentUser, get_db
from src.api.security import (
    create_access_token, hash_password, needs_rehash, verify_password,
)
from src.db import crud, schemas
from src.utils.email import send_password_reset
from src.utils.logging import get_logger
from src.utils.ratelimit import login_limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Annotated[Session, Depends(get_db)]):
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )
    user = crud.create_user(db, email=payload.email, password_hash=hash_password(payload.password))
    return user


@router.post("/login", response_model=schemas.Token)
def login(
        form: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[Session, Depends(get_db)],
):
    key = form.username.lower()
    if not login_limiter.is_allowed(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа, попробуйте позже",
        )

    user = crud.get_user_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        login_limiter.hit(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись отключена",
        )
    if needs_rehash(user.password_hash):
        crud.set_user_password(db, user, hash_password(form.password))
    login_limiter.reset(key)
    token = create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: CurrentUser):
    return current_user


@router.post("/logout", response_model=schemas.MessageOut)
def logout(current_user: CurrentUser):
    return schemas.MessageOut(detail="Выход выполнен")


@router.post("/password-reset/request", response_model=schemas.MessageOut)
def password_reset_request(
        payload: schemas.PasswordResetRequest, db: Annotated[Session, Depends(get_db)]
):
    user = crud.get_user_by_email(db, payload.email)
    if user is not None and user.is_active:
        token = crud.create_reset_token(db, user.id)
        send_password_reset(user.email, token.token)
    return schemas.MessageOut(detail="Если email зарегистрирован, письмо отправлено")


@router.post("/password-reset/confirm", response_model=schemas.MessageOut)
def password_reset_confirm(
        payload: schemas.PasswordResetConfirm, db: Annotated[Session, Depends(get_db)]
):
    token_obj = crud.get_valid_reset_token(db, payload.token)
    if token_obj is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен недействителен или истёк",
        )
    user = crud.get_user(db, token_obj.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен недействителен или истёк",
        )
    crud.set_user_password(db, user, hash_password(payload.new_password))
    crud.consume_reset_token(db, token_obj)
    return schemas.MessageOut(detail="Пароль обновлён")
