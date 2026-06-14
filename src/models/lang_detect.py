from __future__ import annotations

import re


def detect_language(text):
    cyr = len(re.findall(r"[а-яёА-ЯЁ]", text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    total = cyr + lat
    if total == 0:
        return "ru"
    return "ru" if cyr >= lat else "en"