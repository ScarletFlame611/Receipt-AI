"""Поиск чека на фото и выпрямление перспективы.
Резервный метод детекции: ищем самый крупный
четырёхугольный контур и разворачиваем его в прямоугольник.
"""
from __future__ import annotations

import cv2
import numpy as np


def order_points(pts):
    # Упорядочиваем точки как верх-лево, верх-право, низ-право, низ-лево
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    max_width = int(max(width_top, width_bottom))
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    max_height = int(max(height_left, height_right))
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def _largest_quad_from_mask(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, 0.0
    biggest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(biggest)
    peri = cv2.arcLength(biggest, True)
    approx = cv2.approxPolyDP(biggest, 0.02 * peri, True)
    if len(approx) == 4:
        return approx.reshape(4, 2).astype("float32"), area
    box = cv2.boxPoints(cv2.minAreaRect(biggest))
    return box.astype("float32"), area


def find_receipt_contour(gray):
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            np.ones((15, 15), np.uint8), iterations=2)
    quad, _ = _largest_quad_from_mask(mask)
    return quad


def detect_and_warp(image, min_area_ratio=0.15):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if gray.std() < 5:
        return image, False
    quad = find_receipt_contour(gray)
    if quad is None:
        return image, False
    area_ratio = cv2.contourArea(quad) / (image.shape[0] * image.shape[1])
    if area_ratio < min_area_ratio:
        return image, False
    warped = four_point_transform(image, quad)
    return warped, True