"""Инференс-обёртка детектора чека.

Основной путь — обученная YOLOv8: находит чек, берёт самую уверенную рамку,
обрезает по ней. Если YOLO не нашла чек выше порога уверенности, откат на
контурный метод из Блока 2. Настройки читаются из configs/detector.yaml.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.data.perspective import detect_and_warp
from src.utils.config import configs
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Корень проекта: src/models/detector.py -> поднимаемся на три уровня
project_root = Path(__file__).resolve().parent.parent.parent


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else project_root / p


class ReceiptDetector:
    def __init__(self, weights_path=None, conf_threshold=None):
        cfg = configs.detector
        self.weights_path = _resolve(weights_path or cfg.weights_path)
        self.conf_threshold = conf_threshold or cfg.conf_threshold
        self._model = None

    def _load_model(self):
        if self._model is None:
            from ultralytics import YOLO

            if not self.weights_path.exists():
                logger.warning("Веса детектора не найдены: %s", self.weights_path)
                return None
            self._model = YOLO(str(self.weights_path))
        return self._model

    def detect(self, image):
        """Находит чек на изображении (numpy BGR).

        Возвращает (обрезанное_изображение, метод), где метод —
        'yolo', 'contour' или 'none'. При неудаче возвращает исходник.
        """
        model = self._load_model()

        if model is not None:
            result = model(image, conf=self.conf_threshold, verbose=False)[0]
            if len(result.boxes) > 0:
                confs = result.boxes.conf.cpu().numpy()
                best = int(np.argmax(confs))
                x1, y1, x2, y2 = result.boxes.xyxy.cpu().numpy()[best].astype(int)
                crop = image[max(y1, 0):y2, max(x1, 0):x2]
                if crop.size > 0:
                    return crop, "yolo"

        warped, found = detect_and_warp(image)
        return warped, ("contour" if found else "none")