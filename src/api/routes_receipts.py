"""Роуты чеков: загрузка фото → пайплайн → БД, и CRUD своих чеков.

Главная точка стыка ML и бэкенда — POST /: загруженное фото прогоняется через
ReceiptPipeline, результат раскладывается в Receipt + Items. Все операции
изолированы по user_id текущего пользователя.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.dependencies import CurrentUser, get_db, get_pipeline
from src.db import crud, schemas
from src.utils.config import configs, settings
from src.utils.io import pil_to_cv, read_image, save_upload
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/receipts", tags=["receipts"])


def _to_date(value) -> date | None:
    """Пайплайн отдаёт дату ISO-строкой ('ГГГГ-ММ-ДД') или None. Колонка БД
    требует date — парсим, при неудаче возвращаем None (статус останется на
    проверке)."""
    if value is None or isinstance(value, date):
        return value if not isinstance(value, datetime) else value.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _validate_extension(filename: str | None) -> str:
    allowed = configs.app.uploads.allowed_extensions
    ext = (filename or "").rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Недопустимый формат файла. Разрешены: {', '.join(allowed)}",
        )
    return ext


@router.post("", response_model=schemas.ReceiptOut, status_code=status.HTTP_201_CREATED)
def upload_receipt(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    pipeline: Annotated[object, Depends(get_pipeline)],
    file: Annotated[UploadFile, File(...)],
):
    _validate_extension(file.filename)

    data = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пустой файл")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл больше {settings.max_upload_mb} МБ",
        )

    try:
        image = read_image(data)
    except Exception:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Не удалось прочитать изображение")

    # Сохраняем оригинал под UUID-именем (не под именем из загрузки).
    image_path = save_upload(image)

    # Прогон через ML-пайплайн (детектор → OCR → извлечение → категоризация).
    result = pipeline.process(pil_to_cv(image))

    receipt_data = {
        "merchant": result.get("merchant"),
        "purchase_date": _to_date(result.get("date")),
        "total": result.get("total"),
        "receipt_type": result.get("receipt_type"),
        "language": result.get("language"),
        "status": result.get("status", "needs_review"),
        "image_path": image_path,
    }
    receipt = crud.create_receipt(db, current_user.id, receipt_data, result.get("items", []))
    return receipt


@router.get("", response_model=list[schemas.ReceiptOut])
def list_my_receipts(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    return crud.list_receipts(db, current_user.id, limit=limit, offset=offset)


@router.get("/{receipt_id}", response_model=schemas.ReceiptOut)
def get_my_receipt(
    receipt_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    receipt = crud.get_receipt(db, current_user.id, receipt_id)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чек не найден")
    return receipt


@router.put("/{receipt_id}", response_model=schemas.ReceiptOut)
def update_my_receipt(
    receipt_id: int,
    payload: schemas.ReceiptUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    receipt = crud.update_receipt(
        db, current_user.id, receipt_id, payload.model_dump(exclude_unset=True)
    )
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чек не найден")
    return receipt


@router.put("/{receipt_id}/review", response_model=schemas.ReceiptOut)
def review_my_receipt(
    receipt_id: int,
    payload: schemas.ReceiptReview,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Ручная правка: исправленные поля шапки + полная замена позиций."""
    fields = payload.model_dump(exclude={"items"})
    items = [it.model_dump() for it in payload.items]
    receipt = crud.review_receipt(db, current_user.id, receipt_id, fields, items)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чек не найден")
    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_receipt(
    receipt_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    if not crud.delete_receipt(db, current_user.id, receipt_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чек не найден")
    return None
