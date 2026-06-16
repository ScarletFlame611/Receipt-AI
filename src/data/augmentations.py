"""Аугментации для обучения детектора чека.
Имитируют реальные дефекты съёмки: наклон, перспективные искажения,
неравномерную яркость и блики, шум, размытие. Рамка объекта
пересчитывается с изображением.
"""
from __future__ import annotations

import albumentations as A


def build_augmentation_pipeline():
    return A.Compose(
        [
            A.Rotate(limit=12, border_mode=0, p=0.7),
            A.Perspective(scale=(0.02, 0.08), p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.6),
            A.OneOf([
                A.GaussNoise(p=1.0),
                A.ISONoise(p=1.0),
            ], p=0.4),
            A.OneOf([
                A.MotionBlur(blur_limit=5, p=1.0),
                A.GaussianBlur(blur_limit=5, p=1.0),
            ], p=0.3),
            # Имитация блика: яркое пятно на части чека
            A.RandomSunFlare(flare_roi=(0, 0, 1, 1), src_radius=120, p=0.2),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            min_visibility=0.3,
            label_fields=["class_labels"],
        ),
    )


def augment(image, bboxes, class_labels, pipeline=None):
    """Применяет аугментации к изображению и его рамкам.
    """
    pipeline = pipeline or build_augmentation_pipeline()
    result = pipeline(image=image, bboxes=bboxes, class_labels=class_labels)
    return result["image"], result["bboxes"], result["class_labels"]