"""Наполнение БД начальными данными
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.security import hash_password  # noqa: E402
from src.db import models  # noqa: E402
from src.db.base import SessionLocal  # noqa: E402
from src.utils.config import get_configs  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

CATEGORY_COLORS = {
    "Продукты": "#4CAF50",
    "Кафе и рестораны": "#FF9800",
    "Транспорт": "#2196F3",
    "Аптека": "#E91E63",
    "Развлечения": "#9C27B0",
    "Прочее": "#9E9E9E",
}

DEMO_EMAIL = "demo@receipt-ai.local"
DEMO_PASSWORD = "demo12345"

def seed_categories(db) -> dict[str, models.Category]:
    labels = get_configs().categorizer.labels
    result: dict[str, models.Category] = {}
    for name in labels:
        category = db.query(models.Category).filter_by(name=name).one_or_none()
        if category is None:
            category = models.Category(name=name, color=CATEGORY_COLORS.get(name))
            db.add(category)
            logger.info("Категория добавлена: %s", name)
        else:
            category.color = CATEGORY_COLORS.get(name, category.color)
        result[name] = category
    db.commit()
    for category in result.values():
        db.refresh(category)
    return result

def seed_demo(db, categories: dict[str, models.Category]) -> None:
    user = db.query(models.User).filter_by(email=DEMO_EMAIL).one_or_none()
    if user is None:
        user = models.User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Демо-пользователь создан: %s / %s", DEMO_EMAIL, DEMO_PASSWORD)
    if db.query(models.Receipt).filter_by(user_id=user.id).count() == 0:
        receipt = models.Receipt(
            user_id=user.id,
            merchant="Пятёрочка",
            purchase_date=date.today() - timedelta(days=3),
            total=Decimal("254.90"),
            receipt_type="Продукты",
            language="ru",
            status="ok",
        )
        db.add(receipt)
        db.flush()
        products = categories.get("Продукты")
        db.add_all([
            models.Item(receipt_id=receipt.id, name="Молоко Простоквашино 2.5%",
                        good="молоко", brand="Простоквашино", quantity=Decimal("1"),
                        price=Decimal("89.90"),
                        category_id=products.id if products else None),
            models.Item(receipt_id=receipt.id, name="Хлеб Бородинский",
                        good="хлеб", quantity=Decimal("1"), price=Decimal("45.00"),
                        category_id=products.id if products else None),
            models.Item(receipt_id=receipt.id, name="Чай Nesti чёрный",
                        good="чай", brand="Nesti", quantity=Decimal("1"),
                        price=Decimal("120.00"),
                        category_id=products.id if products else None),
        ])
        db.commit()
        logger.info("Демо-чек с позициями добавлен")
    if db.query(models.Budget).filter_by(user_id=user.id).count() == 0:
        products = categories.get("Продукты")
        db.add(models.Budget(
            user_id=user.id,
            category_id=products.id if products else None,
            limit_amount=Decimal("10000.00"),
            period="monthly",
        ))
        db.commit()
        logger.info("Демо-бюджет добавлен")
    if db.query(models.Goal).filter_by(user_id=user.id).count() == 0:
        db.add(models.Goal(
            user_id=user.id,
            title="Накопить на отпуск",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("15000.00"),
            deadline=date.today() + timedelta(days=180),
        ))
        db.commit()
        logger.info("Демо-цель добавлена")


def main() -> None:
    parser = argparse.ArgumentParser(description="Сидинг БД Receipt-AI")
    parser.add_argument("--no-demo", action="store_true", help="Только категории, без демо-данных")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        categories = seed_categories(db)
        if not args.no_demo:
            seed_demo(db, categories)
        logger.info("Сидинг завершён: %d категорий", len(categories))
    finally:
        db.close()


if __name__ == "__main__":
    main()
