"""Скачивание дообученных весов моделей в weights/ по публичным ссылкам Google Drive.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Дообученные веса проекта. ID — публичные ссылки Google Drive
WEIGHTS = [
    {
        "name": "categorizer_real",
        "kind": "zip",
        "gdrive_id": "1YK3Jo7xC97ewNPVt07bAoy68a1giE7lk",
        "marker": "weights/categorizer_real/config.json",
    },
    {
        "name": "donut_sroie",
        "kind": "zip",
        "gdrive_id": "1w4GgDZOhoKr6Q37IpQFL223YaNynL4qp",
        "marker": "weights/donut_sroie/config.json",
    },
    {
        "name": "ner_ru",
        "kind": "zip",
        "gdrive_id": "1-6Ud_Osk9sbygSXfO-ZqJmJWg0Gyk96t",
        "marker": "weights/ner_ru/config.json",
    },
    {
        "name": "detector/best.pt",
        "kind": "file",
        "gdrive_id": "114yEv9vKNS9uoIJrCwzvPTAzXau2KxGQ",
        "marker": "weights/detector/best.pt",
    },
]


def main() -> int:
    weights_dir = PROJECT_ROOT / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    gdown = None
    missing = 0
    for w in WEIGHTS:
        marker = PROJECT_ROOT / w["marker"]
        if marker.exists():
            print(f"[skip] {w['name']} — уже на месте")
            continue
        if gdown is None:
            try:
                import gdown
            except ImportError:
                print("Нужен пакет gdown:  pip install gdown", file=sys.stderr)
                return 1
        print(f"[get ] {w['name']} — качаем с Google Drive...")
        if w["kind"] == "file":
            marker.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=w["gdrive_id"], output=str(marker), quiet=False)
        else:
            zip_path = weights_dir / f"{Path(w['name']).name}.zip"
            gdown.download(id=w["gdrive_id"], output=str(zip_path), quiet=False)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(weights_dir)
            zip_path.unlink(missing_ok=True)
        if marker.exists():
            print(f"[ok  ] {w['name']}")
        else:
            print(
                f"[FAIL] {w['name']}: после скачивания не найден {w['marker']}",
                file=sys.stderr,
            )
            missing += 1
    if missing:
        print(f"\nНе удалось получить моделей: {missing}.", file=sys.stderr)
        return 2
    print("\nГотово: все веса на месте.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
