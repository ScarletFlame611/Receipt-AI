"""Нормализация извлечённых полей чека к единому виду.
"""
from __future__ import annotations

import re
from datetime import datetime

_date_formats = [
    "%d/%m/%Y", "%d-%m-%Y",
    "%d/%m/%y", "%d-%m-%y",
    "%d.%m.%Y", "%d.%m.%y",
]


def normalize_date(raw):
    """Приводит дату к ISO (ГГГГ-ММ-ДД).
    """
    if not raw:
        return None
    text = str(raw).strip()
    for fmt in _date_formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def normalize_amount(raw):
    """Приводит сумму к числу float.
    """
    if raw is None:
        return None
    s = re.sub(r"[^\d.,]", "", str(raw))
    if not s:
        return None

    if "." in s and "," in s:
        # оба разделителя: запятая тысячи, точка десятичная
        s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = parts[0] + "." + parts[1]
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:
        # несколько точек — это разделители тысяч (формат 1.346.000)
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None

def normalize_fields(fields):
    """Применяет нормализацию к структуре полей чека.
    """
    result = dict(fields)
    if "date" in result:
        result["date"] = normalize_date(result.get("date"))
    if "total" in result:
        result["total"] = normalize_amount(result.get("total"))
    return result