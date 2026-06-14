"""Загрузчики и преобразования датасетов CORD и SROIE."""
from __future__ import annotations

from datasets import load_dataset
import json
import random
from pathlib import Path

from src.data.category_data import SHOPS, ITEMS, OTHER_SHOPS, OTHER_ITEMS
from src.utils.config import configs


sroie_tag_names = [
    "O",
    "B-COMPANY", "I-COMPANY",
    "B-DATE", "I-DATE",
    "B-ADDRESS", "I-ADDRESS",
    "B-TOTAL", "I-TOTAL",
]


def decode_sroie_tags(words, ner_tags):
    """Собирает поля чека из слов и их BIO-тегов.

    Слова с тегами B-COMPANY/I-COMPANY склеиваются в название магазина,
    аналогично для даты, адреса и суммы. Возвращает словарь с полями
    и полным текстом чека.
    """
    fields = {"company": [], "date": [], "address": [], "total": []}

    for word, tag in zip(words, ner_tags):
        name = sroie_tag_names[tag] if isinstance(tag, int) else tag
        if name == "O":
            continue
        field = name.split("-", 1)[1].lower()
        if field in fields:
            fields[field].append(word)

    result = {key: " ".join(parts) if parts else None
              for key, parts in fields.items()}
    result["text"] = " ".join(words)
    return result


def load_cord():
    """Читает CORD из кэша HuggingFace. DatasetDict со сплитами train/validation/test."""
    return load_dataset("naver-clova-ix/cord-v2")


def load_sroie():
    """Читает SROIE из кэша HuggingFace. DatasetDict со сплитами train/test."""
    return load_dataset("darentang/sroie", revision="refs/convert/parquet")

def _make_signature(shop, items):
    # Вход модели — ровно то, что соберёт пайплайн: "магазин. товар, товар, ..."
    return f"{shop}. " + ", ".join(items)


def _gen_example(rng, label):
    if label == "Прочее":
        shop = rng.choice(OTHER_SHOPS)
        pool = OTHER_ITEMS
    else:
        shop = rng.choice(SHOPS[label])
        pool = ITEMS[label]
    k = rng.randint(2, 6)
    items = rng.sample(pool, min(k, len(pool)))
    # Иногда подмешиваем 1 шумовой товар, чтобы модель не цеплялась только за позиции
    if label != "Прочее" and rng.random() < 0.15:
        items.append(rng.choice(OTHER_ITEMS))
        rng.shuffle(items)
    return {"text": _make_signature(shop, items), "label": label}


def generate_categorizer_dataset(per_class=500, seed=42):
    rng = random.Random(seed)
    labels = configs.categorizer.labels
    rows = []
    for label in labels:
        seen = set()
        made = 0
        # Тянем уникальные сигнатуры, чтобы не плодить дубли
        while made < per_class:
            ex = _gen_example(rng, label)
            if ex["text"] in seen:
                continue
            seen.add(ex["text"])
            rows.append(ex)
            made += 1
    rng.shuffle(rows)
    return rows


def split_rows(rows, seed=42, ratios=(0.8, 0.1, 0.1)):
    rng = random.Random(seed)
    rng.shuffle(rows)
    n = len(rows)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    return {
        "train": rows[:n_train],
        "validation": rows[n_train:n_train + n_val],
        "test": rows[n_train + n_val:],
    }


def save_categorizer_dataset(out_dir, per_class=500, seed=42):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = generate_categorizer_dataset(per_class=per_class, seed=seed)
    parts = split_rows(rows, seed=seed)
    for name, part in parts.items():
        path = out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {name: len(part) for name, part in parts.items()}


def load_categorizer_dataset(data_dir):
    data = {}
    for name in ["train", "validation", "test"]:
        path = Path(data_dir) / f"{name}.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines()]
        data[name] = rows
    return data