"""Обёртка над OCR-движком (Surya).

Распознаёт текст и его координаты на изображении чека. Используется как
вспомогательный сигнал и как резервный путь извлечения полей по правилам,
если основная модель извлечения выдаёт невалидный результат.

Surya выбран как движок: на русских (кириллических) чеках он читает названия
товаров, магазин, дату и реквизиты заметно лучше PaddleOCR/EasyOCR.
Модели (детекция строк + распознавание) грузятся один раз при первом вызове.
"""
from __future__ import annotations

import cv2
import numpy as np

from src.utils.logging import get_logger

logger = get_logger(__name__)


class OCREngine:
    def __init__(self, langs=("ru", "en")):
        self.langs = list(langs)
        self._rec = None
        self._det = None

    def _load(self):
        if self._rec is None:
            from surya.recognition import RecognitionPredictor
            from surya.detection import DetectionPredictor

            logger.info("Загрузка Surya OCR (langs=%s)", self.langs)
            self._rec = RecognitionPredictor()
            self._det = DetectionPredictor()
        return self._rec, self._det

    @staticmethod
    def _to_pil(image):
        """Принимает путь, numpy BGR (из cv2) или numpy RGB и возвращает PIL RGB."""
        from PIL import Image

        if isinstance(image, (str, bytes)):
            return Image.open(image).convert("RGB")
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        arr = np.asarray(image)
        if arr.ndim == 2:  # серое
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        else:  # cv2 даёт BGR — переводим в RGB
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(arr)

    def recognize(self, image):
        """Распознаёт текст на изображении (numpy BGR, PIL или путь).

        Возвращает список словарей: text, confidence, box (4 точки).
        """
        rec, det = self._load()
        pil = self._to_pil(image)

        preds = rec([pil], [self.langs], det_predictor=det)
        if not preds:
            return []
        results = []
        for line in preds[0].text_lines:
            text = (line.text or "").strip()
            if not text:
                continue
            results.append({
                "text": text,
                "confidence": float(line.confidence or 0.0),
                "box": line.polygon,
            })
        return results

    def full_text(self, image):
        """Возвращает весь распознанный текст одной строкой (для правил и категоризатора)."""
        lines = self.recognize(image)
        return " ".join(item["text"] for item in lines)
