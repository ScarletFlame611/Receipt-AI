#!/usr/bin/env bash
# Точка входа бэкенда: дожидаемся БД (для PostgreSQL), накатываем миграции,
# при необходимости создаём администратора — и запускаем переданную команду
# (по умолчанию uvicorn, см. CMD в Dockerfile).
set -euo pipefail

# --- Ожидание БД (только для внешней СУБД, не для SQLite) ---------------------
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "[entrypoint] Ждём готовности БД..."
  for i in $(seq 1 30); do
    if python -c "
import sys
from sqlalchemy import create_engine, text
from src.utils.config import settings
try:
    create_engine(settings.database_url).connect().execute(text('SELECT 1'))
except Exception as e:
    sys.exit(1)
"; then
      echo "[entrypoint] БД доступна."
      break
    fi
    echo "[entrypoint] БД не готова ($i/30), ждём 2с..."
    sleep 2
  done
fi

# --- Веса моделей (опционально, по публичным ссылкам) -------------------------
# Дообученные веса в git не хранятся. На чистой машине их можно автоматически
# подтянуть с Google Drive (публичные ссылки — тот же источник, что у ноутбуков;
# доступ к чьему-либо личному Drive не нужен). Идемпотентно: уже скачанное
# пропускается. Отключить: FETCH_WEIGHTS=0.
if [[ "${FETCH_WEIGHTS:-1}" != "0" ]]; then
  echo "[entrypoint] Проверяем/докачиваем веса моделей..."
  python scripts/fetch_weights.py \
    || echo "[entrypoint] ВНИМАНИЕ: не все веса скачаны (см. лог выше) — ML-функции могут не работать."
fi

# --- Миграции -----------------------------------------------------------------
# Каталог data нужен для SQLite-варианта (файл БД и загрузки).
mkdir -p data/uploads
echo "[entrypoint] Применяем миграции Alembic..."
alembic upgrade head

# --- Бутстрап администратора (опционально) ------------------------------------
# Если заданы ADMIN_EMAIL и ADMIN_PASSWORD — создаём/повышаем администратора.
if [[ -n "${ADMIN_EMAIL:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
  echo "[entrypoint] Создаём/обновляем администратора ${ADMIN_EMAIL}..."
  python scripts/create_admin.py --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" || true
fi

echo "[entrypoint] Запуск: $*"
exec "$@"
