"""
Для каждой исходной картинки train генерируется несколько аугментированных
копий с синхронно пересчитанными рамками. Результат
сохраняется в новый датасет.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
import cv2

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from src.data.augmentations import build_augmentation_pipeline, augment
from src.utils.logging import get_logger

logger = get_logger(__name__)
src_dir = root / "data" / "raw" / "detector" / "receipt_4dzvu"
dst_dir = root / "data" / "processed" / "detector"
copies_per_image = 4


def read_label(path):
    if not path.exists():
        return [], []
    bboxes, classes = [], []
    for line in path.read_text().strip().splitlines():
        if not line.strip():
            continue
        parts = list(map(float, line.split()))
        classes.append(int(parts[0]))
        bboxes.append(parts[1:])
    return bboxes, classes


def write_label(path, bboxes, classes):
    lines = []
    for cls, box in zip(classes, bboxes):
        coords = " ".join(f"{v:.6f}" for v in box)
        lines.append(f"{cls} {coords}")
    path.write_text("\n".join(lines))


def process_train_split(pipeline):
    img_in = src_dir / "train" / "images"
    lbl_in = src_dir / "train" / "labels"
    img_out = dst_dir / "train" / "images"
    lbl_out = dst_dir / "train" / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)
    images = sorted(img_in.glob("*.jpg"))
    logger.info("Train: %d исходных картинок", len(images))

    for img_path in images:
        bboxes, classes = read_label(lbl_in / (img_path.stem + ".txt"))
        image = cv2.imread(str(img_path))
        # Оригинал
        cv2.imwrite(str(img_out / img_path.name), image)
        write_label(lbl_out / (img_path.stem + ".txt"), bboxes, classes)
        # Аугментированные копии
        if not bboxes:
            continue
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        for k in range(copies_per_image):
            aug_img, aug_boxes, aug_classes = augment(rgb, bboxes, classes, pipeline)
            if not aug_boxes:
                continue
            stem = f"{img_path.stem}_aug{k}"
            out_bgr = cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(img_out / f"{stem}.jpg"), out_bgr)
            write_label(lbl_out / f"{stem}.txt", aug_boxes, aug_classes)

    total = len(list(img_out.glob("*.jpg")))
    logger.info("Train после расширения: %d картинок", total)


def copy_split(split):
    for kind in ["images", "labels"]:
        s = src_dir / split / kind
        d = dst_dir / split / kind
        if s.exists():
            shutil.copytree(s, d, dirs_exist_ok=True)
    logger.info("%s скопирован без изменений", split)


def main():
    dst_dir.mkdir(parents=True, exist_ok=True)
    pipeline = build_augmentation_pipeline()
    process_train_split(pipeline)
    copy_split("valid")
    copy_split("test")
    yaml_text = (
        f"train: {(dst_dir / 'train' / 'images').as_posix()}\n"
        f"val: {(dst_dir / 'valid' / 'images').as_posix()}\n"
        f"test: {(dst_dir / 'test' / 'images').as_posix()}\n"
        f"nc: 1\n"
        f"names: ['Receipt']\n"
    )
    (dst_dir / "data.yaml").write_text(yaml_text)
    logger.info("Готово. data.yaml записан в %s", dst_dir / "data.yaml")


if __name__ == "__main__":
    main()
