"""Тесты нормализации полей чека
"""
from __future__ import annotations

import pytest

from src.models.normalize import normalize_amount, normalize_date, normalize_fields


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("01/06/2019", "2019-06-01"),
        ("01-06-2019", "2019-06-01"),
        ("01/06/19", "2019-06-01"),
        ("01-06-19", "2019-06-01"),
        ("01.06.2019", "2019-06-01"),
        ("01.06.19", "2019-06-01"),
        ("31.12.2020", "2020-12-31"),
        (" 01/06/2019 ", "2019-06-01"),  # пробелы по краям обрезаются
    ],
)
def test_normalize_date_known_formats(raw, expected):
    assert normalize_date(raw) == expected


@pytest.mark.parametrize("empty", [None, ""])
def test_normalize_date_empty_returns_none(empty):
    assert normalize_date(empty) is None


def test_normalize_date_unparseable_returns_input_unchanged():
    assert normalize_date("2019-06-01") == "2019-06-01"
    assert normalize_date("не дата") == "не дата"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("123.45", 123.45),
        ("116.70", 116.70),
        ("123,45", 123.45),
        ("1,234.56", 1234.56),
        ("123,456,789.00", 123456789.00),
        ("1,234", 1234.0),
        ("1.346.000", 1346000.0),
        ("1 234,56", 1234.56),
        ("100.00 руб", 100.0),
        ("₽ 116,70", 116.70),
    ],
)
def test_normalize_amount_formats(raw, expected):
    assert normalize_amount(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", [None, "", "abc", "руб."])
def test_normalize_amount_invalid_returns_none(raw):
    assert normalize_amount(raw) is None


def test_normalize_amount_accepts_numeric_input():
    assert normalize_amount(116.7) == pytest.approx(116.7)


def test_normalize_fields_converts_date_and_total():
    out = normalize_fields(
        {"date": "01/06/2019", "total": "116,70", "company": "Магнит"}
    )
    assert out["date"] == "2019-06-01"
    assert out["total"] == pytest.approx(116.70)
    assert out["company"] == "Магнит"


def test_normalize_fields_missing_keys_no_error():
    out = normalize_fields({"company": "Пятёрочка", "address": "Москва"})
    assert out == {"company": "Пятёрочка", "address": "Москва"}


def test_normalize_fields_returns_new_dict():
    src = {"date": "01/06/2019", "total": "100.00"}
    out = normalize_fields(src)
    assert out is not src
    assert src["date"] == "01/06/2019"
