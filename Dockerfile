# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Backend (FastAPI + ML-пайплайн).
#
# Особенности установки (см. requirements.txt и заметки проекта):
#   * torch/torchvision ставим из CPU-индекса PyTorch, иначе с PyPI тянется
#     огромная CUDA-сборка (несколько ГБ), которая на CPU-инференсе не нужна.
#   * surya-ocr ставим с --no-deps: его пины opencv>=4.11/pillow<11 конфликтуют
#     с пинами проекта (opencv 4.10, pillow 11.0), но по факту он на них работает.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Кэш HuggingFace (Surya, базовые модели NER/категоризатора/donut) —
    # внутри проекта, чтобы примонтировать томом и не качать модели заново.
    HF_HOME=/app/.cache/huggingface

# Системные библиотеки рантайма:
#   libglib2.0-0 — нужна opencv даже в headless-сборке;
#   libgomp1     — OpenMP-рантайм для torch/numpy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости — отдельным слоем для кеширования сборки.
COPY requirements.txt ./

# 1) torch + torchvision из CPU-индекса (без CUDA).
RUN pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cpu

# 2) остальные зависимости (torch уже стоит, surya ставим отдельно ниже).
RUN grep -vE '^(surya-ocr|torch)\b' requirements.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# 3) Surya без зависимостей (см. комментарий в шапке).
RUN pip install --no-cache-dir --no-deps surya-ocr==0.13.1

# Код приложения. weights/ и data/ НЕ копируем — они большие и монтируются
# томами в docker-compose (см. .dockerignore).
COPY . .

# Нормализуем переносы строк (файл мог быть создан на Windows с CRLF) и
# делаем entrypoint исполняемым.
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

# Health-check честный: /api/health отдаёт 200 только когда ML-пайплайн прогрет.
# Первый запуск дольше (Surya/HF-модели качаются), поэтому большой start-period.
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
