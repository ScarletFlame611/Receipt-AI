"""Предобработка изображения чека: оттенки серого, бинаризация, шумоподавление.

Два основных режима выхода задаются уровнем обработки:
  grayscale - оттенки серого, мягкий вариант для Donut
  binary - чёрно-белое изображение, резкий вариант для OCR по правилам
"""
from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image):
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(gray):
    # Медианный фильтр убирает мелкий шум, не размывая края текста так сильно, как обычное гауссово размытие
    return cv2.medianBlur(gray, 3)


def binarize(gray):
    # Адаптивный порог: считается локально, поэтому устойчив к неравномерному освещению и теням, которых в наших фото много
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )


def preprocess(image, level="grayscale"):
    """Прогоняет изображение через очистку и возвращает результат.
    level="grayscale" даёт очищенное полутоновое изображение (для Donut),
    level="binary" дополнительно бинаризует его (для OCR по правилам).
    """
    gray = to_grayscale(image)
    gray = denoise(gray)
    if level == "binary":
        return binarize(gray)
    if level == "grayscale":
        return gray
    raise ValueError(f"неизвестный уровень обработки: {level}")
