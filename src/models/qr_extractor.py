"""Извлечение полей чека из фискального QR-кода (OpenCV).
"""
from __future__ import annotations

from datetime import datetime

import cv2
import numpy as np

from src.utils.logging import get_logger

logger = get_logger(__name__)


def parse_payload(payload):
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
        arr = np.asarray(image)
        yield arr
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if arr.ndim == 3 else arr
        yield gray
        yield cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    def decode(self, image):
        for im in self._variants(image):
            try:
                data, _, _ = self._det.detectAndDecode(im)
            except cv2.error:
                continue
            if data:
                return data
        return None

    def extract(self, image):
        payload = self.decode(image)
        if not payload:
            return None
        parsed = parse_payload(payload)
        if parsed:
            logger.info("QR распознан: date=%s total=%s", parsed["date"], parsed["total"])
        return parsed
