"""Скачивание датасета детекции чеков с Roboflow (workspace ksenia-11).
Рамка вокруг всего чека, один класс receipt. Формат YOLOv8.
Ключ берётся из ROBOFLOW_API_KEY в .env.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv

from src.utils.logging import get_logger

logger = get_logger(__name__)
load_dotenv(root / ".env")

workspace = "ksenia-11"
datasets = [
    {"project": "receipt-4dzvu-yshje", "version": 4, "name": "receipt_4dzvu"},
]


def main():
    from roboflow import Roboflow

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        logger.error("Не задан ROBOFLOW_API_KEY в .env")
        sys.exit(1)

    out_dir = root / "data" / "raw" / "detector"
    out_dir.mkdir(parents=True, exist_ok=True)

    rf = Roboflow(api_key=api_key)
    for ds in datasets:
        target = out_dir / ds["name"]
        logger.info("Скачивание %s/%s v%s", workspace, ds["project"], ds["version"])
        project = rf.workspace(workspace).project(ds["project"])
        project.version(ds["version"]).download("yolov8", location=str(target))
        logger.info("Готово: %s", target)


if __name__ == "__main__":
    main()