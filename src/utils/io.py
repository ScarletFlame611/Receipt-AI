"""Работа с изображениями: чтение, сохранение с UUID-именами."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import pillow_heif  # поддержка HEIC
    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    pass

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def read_image(data: bytes) -> Image.Image:
    img = Image.open(BytesIO(data))
    return img.convert("RGB")


def pil_to_cv(img: Image.Image) -> np.ndarray:
    return np.array(img)[:, :, ::-1].copy()


def cv_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr[:, :, ::-1])


def save_upload(img: Image.Image, ext: str = "jpg") -> str:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext.lower().lstrip('.')}"
    path = upload_dir / name
    img.save(path, quality=95)
    logger.info("Saved upload to %s", path)
    return str(path)


def load_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")