"""Скачивание датасетов чеков для проекта
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
    logger.info("CORD готов, размеры сплитов: %s", sizes)

def download_sroie():
    from datasets import load_dataset
    logger.info("Загрузка SROIE (darentang/sroie, parquet)")
    ds = load_dataset("darentang/sroie", revision="refs/convert/parquet")
    sizes = {split: len(ds[split]) for split in ds}
    logger.info("SROIE готов, размеры сплитов: %s", sizes)

def main():
    download_cord()
    download_sroie()
    logger.info("Оба датасета готовы.")

if __name__ == "__main__":
    main()