"""Определение магазина по справочнику SHOPS """
from src.data.category_data import SHOPS
from src.models.pipeline import ReceiptPipeline


def _pipe():
    p = object.__new__(ReceiptPipeline)
    shops = {s for ss in SHOPS.values() for s in ss}
    p.known_shops = sorted(shops, key=len, reverse=True)
    return p


def _lines(*texts):
    return [{"text": t} for t in texts]


def test_merchant_resolved_from_dictionary_despite_ocr_typo():
    p = _pipe()
    lines = _lines('АП "Тандер', "МАГНИТ-Руанн", "КАССОВЫЙ ЧЕК")
    assert p._guess_merchant(lines) == "Магнит"


def test_merchant_found_mid_text():
    p = _pipe()
    lines = _lines("КАССОВЫЙ ЧЕК", "Место расчетов Магазин Магнит Руанн")
    assert p._guess_merchant(lines) == "Магнит"


def test_merchant_fallback_to_first_line_when_unknown_shop():
    p = _pipe()
    lines = _lines("Кофейня У Дома", "ул. Ленина 5")
    assert p._guess_merchant(lines) == "Кофейня У Дома"


def test_no_false_match_inside_longer_word():
    p = _pipe()
    lines = _lines("Продавец Валентина", "ООО Ромашка")
    assert p._guess_merchant(lines) == "Продавец Валентина"
