"""Подготовка датасета SROIE для дообучения Donut.

Берёт картинки и JSON-разметку полей (company, date, address, total) из
склонированного репозитория ICDAR-2019-SROIE и собирает датасет в формате
imagefolder с metadata.jsonl, который понимает HuggingFace datasets и Donut.

Разбивает 626 чеков на train/validation/test (80/10/10).

Запуск из корня проекта:
    python scripts/prepare_sroie_donut.py
"""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from src.utils.logging import get_logger

logger = get_logger(__name__)

src_root = root / "ICDAR-2019-SROIE" / "data"
img_dir = src_root / "img"
key_dir = src_root / "key"
out_root = root / "data" / "processed" / "sroie_donut"

seed = 42
splits = {"train": 0.8, "validation": 0.1, "test": 0.1}


def load_pairs():
    """Собирает пары (картинка, поля) по совпадающим именам."""
    pairs = []
    for key_path in sorted(key_dir.glob("*.json")):
        img_path = img_dir / (key_path.stem + ".jpg")
        if not img_path.exists():
            continue
        fields = json.loads(key_path.read_text(encoding="utf-8"))
        pairs.append((img_path, fields))
    return pairs


def split_pairs(pairs):
    """Перемешивает и делит на train/validation/test по заданным долям."""
    random.Random(seed).shuffle(pairs)
    n = len(pairs)
    n_train = int(n * splits["train"])
    n_val = int(n * splits["validation"])
    return {
        "train": pairs[:n_train],
        "validation": pairs[n_train:n_train + n_val],
        "test": pairs[n_train + n_val:],
    }


def write_split(name, pairs):
    """Копирует картинки и пишет metadata.jsonl для одного сплита."""
    split_dir = out_root / name
    split_dir.mkdir(parents=True, exist_ok=True)

    meta_lines = []
    for img_path, fields in pairs:
        shutil.copy(img_path, split_dir / img_path.name)
        # Целевая структура для Donut — JSON с полями реквизитов
        gt = {"gt_parse": fields}
        meta_lines.append(json.dumps(
            {"file_name": img_path.name, "ground_truth": json.dumps(gt, ensure_ascii=False)},
            ensure_ascii=False,
        ))

    (split_dir / "metadata.jsonl").write_text("\n".join(meta_lines), encoding="utf-8")
    logger.info("%s: %d чеков", name, len(pairs))


def main():
    pairs = load_pairs()
    logger.info("Всего пар картинка-разметка: %d", len(pairs))

    parts = split_pairs(pairs)
    for name, part in parts.items():
        write_split(name, part)

    logger.info("Готово. Датасет для Donut в %s", out_root)


if __name__ == "__main__":
    main()