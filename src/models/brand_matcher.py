from __future__ import annotations

from pathlib import Path

from src.utils.logging import get_logger

logger = get_logger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent


def _normalize(text):
    return str(text).strip().lower().replace("`", "'").replace("’", "'")


class BrandMatcher:
    def __init__(self, base_path=None, fuzzy_threshold=85, use_embeddings=False):
        self.base_path = Path(base_path) if base_path else project_root / "data" / "processed" / "brand_base.txt"
        self.fuzzy_threshold = fuzzy_threshold
        self.use_embeddings = use_embeddings
        self._brands = None
        self._embedder = None
        self._brand_embeddings = None

    def _load_base(self):
        if self._brands is not None:
            return
        if not self.base_path.exists():
            logger.warning("База брендов не найдена: %s", self.base_path)
            self._brands = []
            return
        raw = [b for b in self.base_path.read_text(encoding="utf-8").splitlines() if b.strip()]
        self._brands = [b for b in raw if len(b) >= 3]
        logger.info("База брендов загружена: %d (из %d, отсеяны короткие)", len(self._brands), len(raw))


    def _load_embedder(self):
        if self._embedder is not None or not self.use_embeddings:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self._brand_embeddings = self._embedder.encode(
                self._brands, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True
            )
            logger.info("Эмбеддинги брендов построены")
        except Exception as e:
            logger.warning("Не удалось включить эмбеддинги: %s", e)
            self.use_embeddings = False

    def _fuzzy(self, query):
        from rapidfuzz import process, fuzz
        match = process.extractOne(query, self._brands, scorer=fuzz.WRatio)
        if match and match[1] >= self.fuzzy_threshold:
            return match[0], match[1]
        return None, 0

    def _semantic(self, query):
        import numpy as np
        self._load_embedder()
        if self._embedder is None:
            return None, 0
        q = self._embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        sims = self._brand_embeddings @ q
        idx = int(sims.argmax())
        return self._brands[idx], float(sims[idx])

    def match(self, brand):
        if not brand:
            return None
        self._load_base()
        if not self._brands:
            return brand
        query = _normalize(brand)

        if query in self._brands:
            return query

        canon, score = self._fuzzy(query)
        if canon:
            return canon

        if self.use_embeddings:
            canon, sim = self._semantic(query)
            if canon and sim >= 0.6:
                return canon

        return query