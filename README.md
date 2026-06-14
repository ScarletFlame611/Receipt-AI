# Receipt-AI

Веб-сервис распознавания чеков: детекция → OCR (Surya) → извлечение полей/позиций
(NER) → категоризация трат, с аналитикой и личным кабинетом.
Бэкенд — FastAPI + ML-пайплайн, фронтенд — React/Vite, БД — PostgreSQL (или SQLite в dev).

## Запуск в Docker

Полный стек (PostgreSQL + бэкенд + фронтенд за nginx) поднимается одной командой.

### Требования
- Docker + Docker Compose
- Каталог `weights/` с весами моделей (детектор, NER, категоризатор, donut) —
  он не в git; смонтируется в контейнер только на чтение.

### Старт
```bash
cp .env.example .env          # при необходимости поправьте JWT_SECRET и пр.
docker compose up --build
```

После сборки:
- Приложение (фронт + проксируемый API): http://localhost:8080
- Swagger бэкенда напрямую: http://localhost:8000/docs

> Первый запуск дольше обычного: контейнер бэкенда докачивает модели Surya и
> базовые модели HuggingFace, затем прогревает пайплайн. До готовности
> `/api/health` отдаёт `503` (это и есть healthcheck). Кэш моделей сохраняется
> в томе `hf_cache`, поэтому повторные запуски быстрые.

### Администратор
Чтобы при старте автоматически создать администратора, задайте в окружении
(или в `.env`) перед `up`:
```bash
ADMIN_EMAIL=admin@receipt-ai.local
ADMIN_PASSWORD=Secret123
```
Либо вручную в уже запущенном контейнере:
```bash
docker compose exec backend python scripts/create_admin.py \
  --email admin@receipt-ai.local --password Secret123
```

### Полезные команды
```bash
docker compose logs -f backend     # логи бэкенда (видно прогрев моделей)
docker compose exec backend alembic upgrade head   # миграции вручную
docker compose down                # остановить
docker compose down -v             # остановить и удалить тома (БД, кэш моделей)
```

## Состав стека (`docker-compose.yml`)
| Сервис     | Что это                                   | Порт   |
|------------|-------------------------------------------|--------|
| `db`       | PostgreSQL 16                             | —      |
| `backend`  | FastAPI + uvicorn, ML-пайплайн            | `8000` |
| `frontend` | Собранный React, раздача и API-прокси (nginx) | `8080` |

Тома: `pgdata` (данные БД), `hf_cache` (кэш моделей). Бинд-маунты: `./weights`
(только чтение), `./data` (загрузки чеков и файл SQLite, если используется).

### Примечания по сборке
- `torch`/`torchvision` ставятся из CPU-индекса PyTorch (без CUDA) — образ
  рассчитан на CPU-инференс.
- `surya-ocr` ставится с `--no-deps` (конфликт пинов opencv/pillow, см. Dockerfile).
