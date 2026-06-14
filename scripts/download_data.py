"""Скачивание датасетов чеков для проекта Receipt-AI.

Скачиваются оба датасета и кэшируются HuggingFace локально:
  CORD  — изображения чеков с разметкой позиций и сумм. Идёт на дообучение Donut.
  SROIE — OCR-слова с BIO-тегами (магазин, дата, адрес, сумма). Без изображений,
          используется как текстовый источник реквизитов и для категоризатора.

После скачивания датасеты читаются из кэша HuggingFace функциями
load_cord() / load_sroie() в src/data/datasets.py — без повторного интернета.

Запуск из корня проекта:
    python scripts/download_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from src.utils.logging import get_logger

logger = get_logger(__name__)


def download_cord():
    from datasets import load_dataset

    logger.info("Загрузка CORD (naver-clova-ix/cord-v2)")
    ds = load_dataset("naver-clova-ix/cord-v2")
    sizes = {split: len(ds[split]) for split in ds}
    logger.info("CORD готов (в кэше HuggingFace), размеры сплитов: %s", sizes)


def download_sroie():
    from datasets import load_dataset

    logger.info("Загрузка SROIE (darentang/sroie, parquet)")
    # Старые репозитории SROIE грузятся через скрипт, который новые версии
    # datasets не поддерживают. Берём авто-сконвертированную parquet-ветку.
    ds = load_dataset("darentang/sroie", revision="refs/convert/parquet")
    sizes = {split: len(ds[split]) for split in ds}
    logger.info("SROIE готов (в кэше HuggingFace), размеры сплитов: %s", sizes)


def main():
    download_cord()
    download_sroie()
    logger.info("Оба датасета готовы.")


if __name__ == "__main__":
    main()