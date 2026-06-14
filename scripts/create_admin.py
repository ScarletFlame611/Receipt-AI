"""Создание (или повышение) администратора.

    python scripts/create_admin.py --email admin@receipt-ai.local --password Secret123

Если пользователь с таким email уже есть — выставляет ему is_admin=True и,
при передаче --password, обновляет пароль. Пароль можно не передавать флагом,
тогда он будет запрошен интерактивно (без эха).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.security import hash_password  # noqa: E402
from src.db import crud, models  # noqa: E402
from src.db.base import SessionLocal  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Создание администратора Receipt-AI")
    parser.add_argument("--email", required=True, help="Email администратора")
    parser.add_argument("--password", help="Пароль (если не задан — спросим интерактивно)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Пароль администратора: ")
    if not password:
        parser.error("Пароль не может быть пустым")

    db = SessionLocal()
    try:
        user = crud.get_user_by_email(db, args.email)
        if user is None:
            user = models.User(
                email=args.email,
                password_hash=hash_password(password),
                is_admin=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
            logger.info("Администратор создан: %s", args.email)
        else:
            user.is_admin = True
            user.is_active = True
            if args.password:
                user.password_hash = hash_password(password)
            db.commit()
            logger.info("Пользователь повышен до администратора: %s", args.email)
    finally:
        db.close()


if __name__ == "__main__":
    main()
