"""Справочные роуты для фронтенда: список категорий (для дропдаунов и подписей)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import CurrentUser, get_db
from src.db import crud, schemas

router = APIRouter(tags=["meta"])


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return crud.list_categories(db)
