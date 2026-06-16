"""Тесты извлечения суммы и даты из текста чека"""
from src.models.field_regex import extract_total, extract_date, extract_fields


def test_total_same_line_anchor():
    assert extract_total("ИТОГ 116.70") == "116.70"


def test_total_anchor_then_next_line():
    assert extract_total("ИТОГ\n116.70\nНаличными 116.70") == "116.70"


def test_total_does_not_merge_across_lines():
    text = "PH KKT 87100001592773051261\n01.06.19 18:16"
    assert extract_total(text) is None


def test_total_does_not_merge_across_spaces():
    text = "ИТОГ 116.70\n01.06.19 18.16"
    assert extract_total(text) == "116.70"


def test_total_ignores_vat_sum_anchor():
    text = "Сумма НДС 20%\n14.97 Сумма НДС 10%\n2.49\nНаличными\n116.70"
    assert extract_total(text) == "116.70"


def test_total_not_fooled_by_zero_cash():
    text = "ИТОГ\n116.70\nналичными 0.00\nбезналичными 116.70 сдача"
    assert extract_total(text) == "116.70"


def test_total_fallback_largest_nonzero():
    text = "ито 116.70\nбулочки 26.90 26.90\nсдача 0.00\nндс 14.97"
    assert extract_total(text) == "116.70"


def test_date_two_digit_year():
    assert extract_date("01.06.19 18:16") == "01.06.19"


def test_extract_fields_receipt_like():
    text = "КАССОВЫЙ ЧЕК\nИТОГ\n116.70\n01.06.19 18:16"
    fields = extract_fields(text)
    assert fields["total"] == "116.70"
    assert fields["date"] == "01.06.19"
