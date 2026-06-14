"""Обучение детектора чека на YOLOv8.
Дообучает предобученную YOLOv8 на датасете детекции (один класс receipt).
"""
from __future__ import annotations

from pathlib import Path


def train_detector(
    data_yaml,
    base_model="yolov8n.pt",
    epochs=60,
    imgsz=640,
    batch=16,
    project="runs/detector",
    name="receipt_yolo",
    device=None,
):
    """Дообучает YOLOv8 на детекцию чека.
    data_yaml - путь к data.yaml датасета. base_model - предобученные веса. Возвращает
    объект обученной модели и путь к лучшим весам.
    """
    from ultralytics import YOLO

    model = YOLO(base_model)
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=project,
        name=name,
        device=device,
        patience=15,
        plots=True,
    )

    best_weights = Path(project) / name / "weights" / "best.pt"
    return model, best_weights


def validate_detector(weights, data_yaml, imgsz=640):
    """Прогоняет валидацию обученной модели, возвращает метрики (mAP, precision, recall)."""
    from ultralytics import YOLO

    model = YOLO(str(weights))
    metrics = model.val(data=str(data_yaml), imgsz=imgsz)
    return metrics