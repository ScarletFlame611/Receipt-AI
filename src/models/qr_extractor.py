"""Извлечение полей чека из фискального QR-кода (OpenCV).

Российский кассовый чек кодирует в QR строку вида
    t=ГГГГММДДTЧЧММ&s=СУММА&fn=...&i=...&fp=...&n=...
То есть дата и итоговая сумма лежат там в явном виде — это надёжнее OCR именно
для этих двух полей (детерминированно и точно).

Декодируем штатным cv2.QRCodeDetector: не требует системных зависимостей
(в отличие от pyzbar/zbar, которому на Windows нужна libzbar/VC++ Redist) и
устойчив к повороту чека. Жёсткую бинаризацию НЕ применяем — она ломает QR.
"""
from __future__ import annotations

from datetime import datetime

import cv2
import numpy as np

from src.utils.logging import get_logger

logger = get_logger(__name__)


def parse_payload(payload):
    """Разбирает строку QR фискального чека в поля.

    Возвращает dict (date ISO, time, total, fn, i, fp, n, raw) или None,
    если это не похоже на чек (нет ни суммы, ни даты)."""
    if not payload:
        return None
    fields = {}
    for part in payload.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    if "t" not in fields and "s" not in fields:
        return None

    date_iso = time_str = None
    raw_t = fields.get("t", "")
    # Порядок важен: формат без секунд ("...T1816") пробуем первым, иначе
    # секундный формат жадно прочёл бы "1816" как 18:01:06. Для строки с
    # секундами ("...T181605") формат без секунд оставит хвост → ValueError →
    # перейдём к секундному.
    for fmt in ("%Y%m%dT%H%M", "%Y%m%dT%H%M%S"):
        try:
            dt = datetime.strptime(raw_t, fmt)
            date_iso = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M")
            break
        except ValueError:
            continue

    return {
        "date": date_iso,
        "time": time_str,
        "total": fields.get("s"),
        "fn": fields.get("fn"),
        "i": fields.get("i"),
        "fp": fields.get("fp"),
        "n": fields.get("n"),
        "raw": payload,
    }


class QRExtractor:
    def __init__(self):
        self._det = cv2.QRCodeDetector()

    def _variants(self, image):
        # Лёгкие варианты входа: оригинал, серый, увеличенный. Без бинаризации.
        arr = np.asarray(image)
        yield arr
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if arr.ndim == 3 else arr
        yield gray
        yield cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    def decode(self, image):
        """Возвращает строку QR или None, перебирая варианты входа."""
        for im in self._variants(image):
            try:
                data, _, _ = self._det.detectAndDecode(im)
            except cv2.error:
                continue
            if data:
                return data
        return None

    def extract(self, image):
        """Декодирует QR и разбирает поля чека.

        None, если QR нет или он не похож на фискальный чек."""
        payload = self.decode(image)
        if not payload:
            return None
        parsed = parse_payload(payload)
        if parsed:
            logger.info("QR распознан: date=%s total=%s", parsed["date"], parsed["total"])
        return parsed
