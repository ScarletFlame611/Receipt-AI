import re
from pathlib import Path

from src.models.normalize import normalize_amount
from src.utils.config import configs
from src.utils.logging import get_logger

logger = get_logger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent
base_model = configs.donut.base_model

field_prompt = configs.donut.fields.task_prompt
field_order = configs.donut.fields.field_order
sroie_tokens = [
    field_prompt, "</s_sroie>",
    "<s_company>", "</s_company>",
    "<s_date>", "</s_date>",
    "<s_address>", "</s_address>",
    "<s_total>", "</s_total>",
]
items_prompt = configs.donut.items.task_prompt


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else project_root / p


def _pick_device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


# Поля чека — наша дообученная на SROIE модель (магазин/дата/адрес/сумма)
class FieldExtractor:
    def __init__(self, weights_path=None, max_length=None):
        cfg = configs.donut.fields
        self.weights_path = _resolve(weights_path or cfg.weights_path)
        self.max_length = max_length or cfg.max_length
        self._model = None
        self._processor = None
        self._device = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import DonutProcessor, VisionEncoderDecoderModel
        if not self.weights_path.exists():
            logger.warning("Веса Donut (поля) не найдены: %s", self.weights_path)
            return
        self._processor = DonutProcessor.from_pretrained(base_model)
        self._processor.tokenizer.add_special_tokens({"additional_special_tokens": sroie_tokens})
        self._model = VisionEncoderDecoderModel.from_pretrained(str(self.weights_path))
        self._device = _pick_device()
        self._model.to(self._device)
        self._model.eval()
        logger.info("Donut-поля загружен на %s", self._device)

    def extract(self, image):
        self._load()
        if self._model is None:
            return {f: None for f in field_order}
        import torch
        pixel_values = self._processor(image.convert("RGB"), return_tensors="pt").pixel_values.to(self._device)
        decoder_input_ids = self._processor.tokenizer(
            field_prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self._device)
        with torch.no_grad():
            outputs = self._model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.max_length,
                pad_token_id=self._processor.tokenizer.pad_token_id,
                eos_token_id=self._processor.tokenizer.eos_token_id,
                use_cache=True,
                bad_words_ids=[[self._processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )
        seq = self._processor.batch_decode(outputs.sequences)[0]
        seq = seq.replace(self._processor.tokenizer.eos_token, "").replace(field_prompt, "")
        parsed = self._processor.token2json(seq)
        return {f: parsed.get(f) if isinstance(parsed, dict) else None for f in field_order}


# Позиции — исходная CORD-модель из коробки, режим <s_cord-v2> отдаёт menu
class ItemsExtractor:
    def __init__(self, max_length=None):
        self.max_length = max_length or configs.donut.items.max_length
        self._model = None
        self._processor = None
        self._device = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import DonutProcessor, VisionEncoderDecoderModel
        self._processor = DonutProcessor.from_pretrained(base_model)
        self._model = VisionEncoderDecoderModel.from_pretrained(base_model)
        self._device = _pick_device()
        self._model.to(self._device)
        self._model.eval()
        logger.info("Donut-позиции (CORD) загружен на %s", self._device)

    def extract(self, image):
        self._load()
        import torch
        pixel_values = self._processor(image.convert("RGB"), return_tensors="pt").pixel_values.to(self._device)
        decoder_input_ids = self._processor.tokenizer(
            items_prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self._device)
        with torch.no_grad():
            outputs = self._model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.max_length,
                pad_token_id=self._processor.tokenizer.pad_token_id,
                eos_token_id=self._processor.tokenizer.eos_token_id,
                use_cache=True,
                bad_words_ids=[[self._processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )
        seq = self._processor.batch_decode(outputs.sequences)[0]
        seq = seq.replace(self._processor.tokenizer.eos_token, "").replace(items_prompt, "")
        parsed = self._processor.token2json(seq)
        return _parse_cord_menu(parsed)


# CORD кладёт позиции в menu; поля называются nm (название), cnt (кол-во), price
def _parse_cord_menu(parsed):
    if not isinstance(parsed, dict):
        return []
    menu = parsed.get("menu")
    if menu is None:
        return []
    if isinstance(menu, dict):  # один товар CORD отдаёт не списком, а объектом
        menu = [menu]
    items = []
    for entry in menu:
        if not isinstance(entry, dict):
            continue
        name = entry.get("nm")
        if not name:
            continue
        items.append({
            "name": str(name).strip(),
            "quantity": _to_number(entry.get("cnt")),
            "price": normalize_amount(entry.get("price")),
        })
    return items


# Количество — простое число, не денежная сумма, поэтому без локали
def _to_number(raw):
    if raw is None:
        return None
    s = re.sub(r"[^\d.]", "", str(raw))
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# Резерв: позиции из OCR-строк, когда CORD-модель вернула пусто/мусор.
# Берём строки, где есть и текст, и цена в конце.
_price_re = re.compile(r"(.+?)\s+(\d+[.,]\d{2})\s*$")


def parse_items_from_ocr(ocr_lines):
    items = []
    for line in ocr_lines:
        text = line.get("text", "") if isinstance(line, dict) else str(line)
        m = _price_re.match(text.strip())
        if not m:
            continue
        name = m.group(1).strip()
        if len(name) < 2:
            continue
        items.append({"name": name, "quantity": None, "price": normalize_amount(m.group(2))})
    return items


# Общий вход: склеивает поля и позиции, позиции с резервом на OCR
class ReceiptExtractor:
    def __init__(self, weights_path=None):
        self.fields = FieldExtractor(weights_path)
        self.items = ItemsExtractor()

    def extract(self, image, ocr_lines=None):
        result = self.fields.extract(image)
        items = self.items.extract(image)
        items_source = "model" if items else "none"
        if not items and ocr_lines:
            items = parse_items_from_ocr(ocr_lines)
            if items:
                items_source = "ocr"
                logger.info("Позиции взяты из OCR-резерва: %d шт", len(items))
        result["items"] = items
        result["items_source"] = items_source
        return result