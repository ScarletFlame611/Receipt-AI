from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from src.data.category_data import SHOPS
from src.models.detector import ReceiptDetector
from src.models.ocr import OCREngine
from src.models.qr_extractor import QRExtractor
from src.models.ner_extractor import NERExtractor
from src.models.brand_matcher import BrandMatcher
from src.models.categorizer import SpendingCategorizer
from src.models.field_regex import extract_fields
from src.models.lang_detect import detect_language
from src.models.normalize import normalize_date, normalize_amount
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Сумма вида 26.90 / 39,90 / "39 90" (OCR часто разрывает копейки пробелом).
_AMOUNT_RE = re.compile(r"(\d{1,6})[.,\s](\d{2})(?!\d)")
_LETTERS_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")

# Строки-реквизиты, которые не являются товаром, даже если NER что-то в них
# нашёл (типичные ложные срабатывания: "HAC 20%" → бренд, "ИТОГ" → товар).
_JUNK_RE = re.compile(
    r"(нд[сc]|на[сc]|hac)\b.*\d+\s*%"          # строка НДС/НАС/HAC X%
    r"|\bито|\bвсего\b|к оплате"                # блок итогов (ИТОГ/ИТО/итол…)
    r"|наличны|безналичны|сдача|\bсумма\b"
    r"|\bкарт|оплат|кассир|товаровед|продав"
    r"|\bсмена\b|\bкасса\b|\bчек\b|\bинн\b|\bофд\b|\bккт\b"
    r"|\bфн\b|\bфд\b|\bфп\b|сайт|место расч"
    r"|кол-?\s?во|\bцена\b|скидк|акци|подробности|издели",
    re.IGNORECASE,
)


def _bounds(box):
    """Габариты полигона строки: (x0, x1, y0, y1, y_center)."""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), max(xs), min(ys), max(ys), (min(ys) + max(ys)) / 2


def _amounts(text):
    """Все денежные суммы в строке как (значение, позиция_конца)."""
    return [(float(f"{m.group(1)}.{m.group(2)}"), m.end())
            for m in _AMOUNT_RE.finditer(text)]


class ReceiptPipeline:
    def __init__(self):
        self.detector = ReceiptDetector()
        self.ocr = OCREngine()
        self.qr = QRExtractor()
        self.ner = NERExtractor()
        self.brand_matcher = BrandMatcher()
        self.categorizer = SpendingCategorizer()
        # Каноничные имена сетей из того же справочника, что и у категоризатора.
        # Длинные имена первыми — чтобы предпочесть более специфичное совпадение.
        shops = {shop for shops in SHOPS.values() for shop in shops}
        self.known_shops = sorted(shops, key=len, reverse=True)

    def _match_known_shop(self, lines):
        """Ищет в строках OCR известную сеть из справочника и возвращает её
        каноничное имя. Это устойчивее, чем брать первую строку: имя сети на
        чеке часто искажено (АО→АП) или соседствует с реквизитами, а по
        справочнику мы находим её где угодно ("МАГНИТ-Руанн", "Магазин Магнит")
        и отдаём чистое "Магнит", которое затем поймает правило категоризатора."""
        for item in lines:
            low = item["text"].lower()
            for shop in self.known_shops:
                if re.search(rf"\b{re.escape(shop.lower())}\b", low):
                    return shop
        return None

    def _guess_merchant(self, lines):
        shop = self._match_known_shop(lines)
        if shop:
            return shop
        # Резерв: первая осмысленная (не из одних цифр) строка
        for item in lines:
            t = item["text"].strip()
            if len(t) >= 3 and not t.replace(" ", "").isdigit():
                return t
        return None

    def _item_region(self, lines):
        """Сужает строки до товарной зоны: между шапкой колонок (КОЛ-ВО/ЦЕНА)
        и блоком итогов (ИТОГ/НАЛИЧНЫМИ/СУММА НДС). Так NER не цепляет товары
        из рекламной шапки и реквизитов внизу чека. Если границы не нашлись —
        возвращает все строки (поведение как раньше)."""
        texts = [item["text"].lower() for item in lines]
        start, end = 0, len(lines)
        for i, low in enumerate(texts):
            if "кол-во" in low or "колво" in low or "кол во" in low:
                start = i + 1
                break
        for i in range(start, len(lines)):
            low = texts[i]
            if low.startswith("итог") or "наличными" in low or "сумма ндс" in low:
                end = i
                break
        return lines[start:end] if start < end else lines

    def _line_total(self, name_item, lines, line_h, img_right):
        """Сумма позиции = число в правой колонке (x ≈ правый край) на строке
        под названием. Так берём итог по строке, а не объём/цену-со-скидкой из
        соседних колонок. Если цена на самой строке названия (другой layout) —
        берём последнюю сумму в её правой части.

        Возвращает (price, name) — name может быть укорочен, если цена была
        внутри строки названия."""
        x0, x1, y0, y1, yc = _bounds(name_item["box"])
        right_min = 0.55 * img_right  # «правая» колонка — сумма по строке

        # 1) сумма на отдельной строке ниже названия, в правой колонке
        best = None  # (x1_кандидата, значение)
        for other in lines:
            if other is name_item or not other.get("box"):
                continue
            ox0, ox1, oy0, oy1, oyc = _bounds(other["box"])
            if ox1 < right_min:
                continue
            if not (yc - 0.5 * line_h <= oyc <= yc + 2.5 * line_h):
                continue
            amts = _amounts(other["text"])
            if not amts:
                continue
            if best is None or ox1 > best[0]:
                best = (ox1, amts[-1][0])
        if best is not None:
            return best[1], name_item["text"].strip()

        # 2) цена в самой строке названия (если строка достаёт до правого края)
        text = name_item["text"].strip()
        if x1 >= 0.85 * img_right:
            amts = _amounts(text)
            if amts:
                value, end = amts[-1]
                return value, text[:end - len(f"{value:.2f}")].strip(" .,-")
        return None, text

    def _extract_items(self, lines):
        boxed = [l for l in lines if l.get("box")]
        heights = sorted(_bounds(l["box"])[3] - _bounds(l["box"])[2] for l in boxed)
        line_h = heights[len(heights) // 2] if heights else 15.0
        img_right = max((_bounds(l["box"])[1] for l in boxed), default=0.0)

        items = []
        for item in self._item_region(lines):
            text = item["text"].strip()
            if len(text) < 3 or not _LETTERS_RE.search(text):
                continue
            if _JUNK_RE.search(text):  # реквизиты/итоги — не товар, вето над NER
                continue
            price, name = self._line_total(item, lines, line_h, img_right)
            res = self.ner.extract(name)
            goods = res["goods"]
            brands = res["brands"]
            # Товар, если NER нашёл good/brand ИЛИ к строке привязалась сумма.
            if not goods and not brands and price is None:
                continue
            brand_raw = brands[0] if brands else None
            brand = self.brand_matcher.match(brand_raw) if brand_raw else None
            items.append({
                "name": name,
                "good": goods[0] if goods else None,
                "brand": brand,
                "price": self._to_decimal(price),
            })
        return items

    def _to_decimal(self, value):
        if value is None:
            return None
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return None

    def _quality_status(self, merchant, date, total, items):
        has_key = merchant and date and total
        if has_key and items:
            return "ok"
        if not (date or total) and not items:
            return "failed"
        return "needs_review"

    def process(self, image):
        crop, method = self.detector.detect(image)
        logger.info("Детекция: метод=%s", method)

        lines = self.ocr.recognize(crop)
        full_text = " ".join(l["text"] for l in lines)

        if not full_text.strip():
            return {
                "merchant": None, "date": None, "total": None,
                "language": None, "receipt_type": None,
                "items": [], "qr": None, "status": "failed",
            }

        language = detect_language(full_text)
        text_lines = "\n".join(l["text"] for l in lines)
        fields = extract_fields(text_lines)
        merchant = self._guess_merchant(lines)
        items = self._extract_items(lines)

        sig_items = [{"name": " ".join(filter(None, [it["good"], it["brand"]]))} for it in items]
        cat = self.categorizer.categorize(merchant, sig_items)

        # Фискальный QR (если есть и читаем) — источник истины для даты и суммы:
        # точнее OCR. Декодируем по оригиналу, т.к. детектор мог обрезать QR.
        # Регэксп по тексту OCR остаётся фолбэком, когда QR нет/не читается.
        qr = self.qr.extract(image)

        date_src = (qr and qr.get("date")) or fields.get("date")
        total_src = (qr and qr.get("total")) or fields.get("total")
        date_norm = normalize_date(date_src) if date_src else None
        total_norm = normalize_amount(total_src) if total_src else None

        status = self._quality_status(merchant, date_norm, total_norm, items)

        return {
            "merchant": merchant,
            "date": date_norm,
            "total": self._to_decimal(total_norm),
            "language": language,
            "receipt_type": cat["category"],
            "items": items,
            "qr": qr,
            "status": status,
        }