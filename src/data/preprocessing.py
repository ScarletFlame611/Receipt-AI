"""Предобработка изображения чека
"""
from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image):
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(gray):
    return cv2.medianBlur(gray, 3)


def binarize(gray):
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )


def preprocess(image, level="grayscale"):
    gray = to_grayscale(image)
    gray = denoise(gray)
    if level == "binary":
        return binarize(gray)
    if level == "grayscale":
        return gray
    raise ValueError(f"неизвестный уровень обработки: {level}")
