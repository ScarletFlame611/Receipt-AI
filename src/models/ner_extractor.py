from __future__ import annotations

import re
from pathlib import Path

from src.utils.config import configs
from src.utils.logging import get_logger

logger = get_logger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent

BASE_TOKENIZER = "xlm-roberta-base"
_token_re = re.compile(r"[A-Za-zА-Яа-яЁё]+|\d+|[^\sA-Za-zА-Яа-яЁё\d]", re.UNICODE)


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else project_root / p


def _normalize(text):
    return str(text).replace("`", "'").replace("’", "'").replace("´", "'")


def _tokenize_words(text):
    return _token_re.findall(_normalize(text))


class NERExtractor:
    def __init__(self, weights_path=None):
        self.weights_path = _resolve(weights_path or "weights/ner_ru")
        self.max_length = 64
        self._model = None
        self._tokenizer = None
        self._device = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        if not self.weights_path.exists():
            logger.warning("Веса NER не найдены: %s", self.weights_path)
            return
        self._tokenizer = AutoTokenizer.from_pretrained(BASE_TOKENIZER)
        self._model = AutoModelForTokenClassification.from_pretrained(str(self.weights_path))
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device)
        self._model.eval()
        self.id2label = self._model.config.id2label
        logger.info("NER загружен на %s", self._device)

    def _predict_word_tags(self, words):
        import torch

        enc = self._tokenizer(
            words,
            is_split_into_words=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            logits = self._model(**enc).logits[0]
        pred_ids = logits.argmax(-1).tolist()

        word_ids = enc.word_ids(batch_index=0)
        tags = [None] * len(words)
        prev = None
        for idx, wid in enumerate(word_ids):
            if wid is not None and wid != prev:
                tags[wid] = self.id2label[pred_ids[idx]]
            prev = wid
        return ["O" if t is None else t for t in tags]

    def _collect(self, words, tags, entity):
        results, cur = [], []
        b_tag, i_tag = f"B-{entity}", f"I-{entity}"
        for w, t in zip(words, tags):
            if t == b_tag:
                if cur:
                    results.append(" ".join(cur))
                cur = [w]
            elif t == i_tag:
                cur.append(w)
            else:
                if cur:
                    results.append(" ".join(cur))
                    cur = []
        if cur:
            results.append(" ".join(cur))
        return results

    def extract(self, text):
        self._load()
        if self._model is None:
            return {"goods": [], "brands": []}
        words = _tokenize_words(text)
        if not words:
            return {"goods": [], "brands": []}
        tags = self._predict_word_tags(words)
        return {
            "goods": self._collect(words, tags, "GOOD"),
            "brands": self._collect(words, tags, "BRAND"),
        }