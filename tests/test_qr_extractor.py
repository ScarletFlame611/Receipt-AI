"""Разбор фискальной строки QR-кода чека """
from src.models.qr_extractor import parse_payload


REAL = "t=20190601T1816&s=116.70&fn=8710000100599125&i=31025&fp=1329692305&n=1"


def test_parse_real_receipt_qr():
    p = parse_payload(REAL)
    assert p["date"] == "2019-06-01"
    assert p["time"] == "18:16"
    assert p["total"] == "116.70"
    assert p["fn"] == "8710000100599125"
    assert p["i"] == "31025"
    assert p["fp"] == "1329692305"
    assert p["n"] == "1"


def test_parse_with_seconds_in_time():
    p = parse_payload("t=20190601T181605&s=116.70&fp=1")
    assert p["date"] == "2019-06-01"
    assert p["time"] == "18:16"


def test_parse_unparseable_time_keeps_total():
    p = parse_payload("t=BADDATE&s=116.70")
    assert p is not None
    assert p["date"] is None
    assert p["total"] == "116.70"


def test_non_receipt_payload_rejected():
    assert parse_payload("https://example.com") is None
    assert parse_payload("") is None
    assert parse_payload(None) is None
