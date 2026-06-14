# Категоризатор трат: правила по магазину → BERT по сигнатуре → "Прочее".
# Правила идут первыми: известную сеть классифицируем мгновенно и точно,
# не нагружая модель. Модель — для всего, что правила не покрыли.
from __future__ import annotations

from pathlib import Path

from src.data.category_data import SHOPS
from src.utils.config import configs
from src.utils.logging import get_logger

logger = get_logger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent
DEFAULT_CATEGORY = "Прочее"


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else project_root / p


def _build_shop_rules():
    # Словарь "магазин в нижнем регистре → категория" из тех же справочников
    rules = {}
    for category, shops in SHOPS.items():
        for shop in shops:
            rules[shop.lower()] = category
    return rules


class SpendingCategorizer:
    def __init__(self, weights_path=None):
        cfg = configs.categorizer
        self.labels = cfg.labels
        self.max_length = cfg.max_length
        self.threshold = cfg.inference.confidence_threshold
        self.weights_path = _resolve(weights_path or cfg.weights_path)
        self.shop_rules = _build_shop_rules()
        self._model = None
        self._tokenizer = None
        self._device = None

    def _match_rule(self, company):
        if not company:
            return None
        low = company.lower().strip()
        # Точное совпадение, затем вхождение известной сети в строку
        if low in self.shop_rules:
            return self.shop_rules[low]
        for shop, category in self.shop_rules.items():
            if shop in low:
                return category
        return None

    def _load_model(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        if not self.weights_path.exists():
            logger.warning("Веса категоризатора не найдены: %s", self.weights_path)
            return
        self._tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
        self._model = AutoModelForSequenceClassification.from_pretrained(str(self.weights_path))
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device)
        self._model.eval()
        logger.info("Категоризатор загружен на %s", self._device)

    def _predict_model(self, text):
        self._load_model()
        if self._model is None:
            return None, 0.0
        import torch
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True,
            max_length=self.max_length, padding=True,
        ).to(self._device)
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        idx = int(torch.argmax(probs))
        return self.labels[idx], float(probs[idx])

    def _make_signature(self, company, items):
        names = [i.get("name", "") for i in (items or []) if i.get("name")]
        head = company or ""
        if names:
            return f"{head}. " + ", ".join(names)
        return head

    def categorize(self, company, items=None):
        # 1) правила по магазину
        rule_cat = self._match_rule(company)
        if rule_cat is not None:
            return {"category": rule_cat, "source": "rule", "confidence": 1.0}
        # 2) модель по сигнатуре магазин+позиции
        text = self._make_signature(company, items)
        if text.strip():
            label, conf = self._predict_model(text)
            if label is not None and conf >= self.threshold:
                return {"category": label, "source": "model", "confidence": conf}
        # 3) fallback
        return {"category": DEFAULT_CATEGORY, "source": "fallback", "confidence": 0.0}