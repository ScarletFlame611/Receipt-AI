from __future__ import annotations

import re

DATE_PATTERNS = [
    r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
    r"\b(\d{2}[./-]\d{2}[./-]\d{2})\b",
    r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
]

TOTAL_ANCHORS = [
    "итог", "к оплате", "всего",
    "total", "amount", "balance due",
]

_amount_re = re.compile(r"(\d+[.,]\d{2})")
_date_re = re.compile(r"\d{2}[./-]\d{2}[./-]\d{2,4}")


def extract_date(text):
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def extract_total(text):
    dates = set(_date_re.findall(text))

    def clean_amounts(s):
        result = []
        for m in _amount_re.finditer(s):
            val = m.group(1)
            inside_date = any(val in d for d in dates)
            if not inside_date:
                result.append(val)
        return result

    lines = text.splitlines() if "\n" in text else [text]

    for i, line in enumerate(lines):
        low = line.lower()
        for anchor in TOTAL_ANCHORS:
            pos = low.find(anchor)
            if pos == -1:
                continue
            amounts = clean_amounts(line[pos + len(anchor):])
            if not amounts and i + 1 < len(lines):
                amounts = clean_amounts(lines[i + 1])
            if amounts:
                return amounts[0].replace(" ", "")

    amounts = [a.replace(" ", "") for a in clean_amounts(text) if _to_float(a) > 0]
    if amounts:
        return max(amounts, key=_to_float)
    return None


def _to_float(s):
    s = s.replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_fields(text):
    return {
        "date": extract_date(text),
        "total": extract_total(text),
    }
