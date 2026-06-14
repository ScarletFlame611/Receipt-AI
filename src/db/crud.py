from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.db import models


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.execute(
        select(models.User).where(models.User.email == email)
    ).scalar_one_or_none()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)


def create_user(db: Session, email: str, password_hash: str, is_admin: bool = False) -> models.User:
    user = models.User(email=email, password_hash=password_hash, is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_receipt(db: Session, user_id: int, data: dict, items: list[dict]) -> models.Receipt:
    receipt = models.Receipt(
        user_id=user_id,
        merchant=data.get("merchant"),
        purchase_date=data.get("purchase_date"),
        total=data.get("total"),
        receipt_type=data.get("receipt_type"),
        language=data.get("language"),
        status=data.get("status", "needs_review"),
        image_path=data.get("image_path"),
    )
    db.add(receipt)
    db.flush()
    for it in items:
        db.add(models.Item(
            receipt_id=receipt.id,
            name=it.get("name", ""),
            good=it.get("good"),
            brand=it.get("brand"),
            quantity=it.get("quantity"),
            price=it.get("price"),
            category_id=it.get("category_id"),
        ))
    db.commit()
    db.refresh(receipt)
    return receipt


def get_receipt(db: Session, user_id: int, receipt_id: int) -> Optional[models.Receipt]:
    return db.execute(
        select(models.Receipt)
        .where(models.Receipt.id == receipt_id, models.Receipt.user_id == user_id)
        .options(selectinload(models.Receipt.items))
    ).scalar_one_or_none()


def list_receipts(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> list[models.Receipt]:
    return db.execute(
        select(models.Receipt)
        .where(models.Receipt.user_id == user_id)
        .order_by(models.Receipt.created_at.desc())
        .limit(limit).offset(offset)
        .options(selectinload(models.Receipt.items))
    ).scalars().all()


def update_receipt(db: Session, user_id: int, receipt_id: int, fields: dict) -> Optional[models.Receipt]:
    receipt = get_receipt(db, user_id, receipt_id)
    if receipt is None:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(receipt, key):
            setattr(receipt, key, value)
    db.commit()
    db.refresh(receipt)
    return receipt


def delete_receipt(db: Session, user_id: int, receipt_id: int) -> bool:
    receipt = get_receipt(db, user_id, receipt_id)
    if receipt is None:
        return False
    db.delete(receipt)
    db.commit()
    return True


def list_categories(db: Session) -> list[models.Category]:
    return db.execute(
        select(models.Category).order_by(models.Category.name)
    ).scalars().all()


def summary_by_category(db: Session, user_id: int) -> list[dict]:
    """Траты по категории ЧЕКА (receipt_type), а не по категории товара.

    Категория чека проставляется категоризатором (см. pipeline), тогда как
    item.category_id почти всегда пуст — поэтому разбивка строится по чекам.
    """
    rows = db.execute(
        select(models.Receipt.receipt_type, func.sum(models.Receipt.total))
        .where(
            models.Receipt.user_id == user_id,
            models.Receipt.receipt_type.isnot(None),
        )
        .group_by(models.Receipt.receipt_type)
        .order_by(func.sum(models.Receipt.total).desc())
    ).all()
    return [
        {"category": receipt_type, "total": float(total or 0)}
        for receipt_type, total in rows
    ]


def receipts_count(db: Session, user_id: int) -> int:
    return int(db.execute(
        select(func.count(models.Receipt.id))
        .where(models.Receipt.user_id == user_id)
    ).scalar() or 0)


def spending_total(db: Session, user_id: int) -> float:
    total = db.execute(
        select(func.sum(models.Receipt.total))
        .where(models.Receipt.user_id == user_id)
    ).scalar()
    return float(total or 0)


def review_receipt(
    db: Session, user_id: int, receipt_id: int, fields: dict, items: list[dict]
) -> Optional[models.Receipt]:
    """Ручная правка: обновляет шапку и ПОЛНОСТЬЮ заменяет позиции.

    Изоляция по user_id: чужой чек не найдётся и вернётся None.
    """
    receipt = get_receipt(db, user_id, receipt_id)
    if receipt is None:
        return None

    for key, value in fields.items():
        if value is not None and hasattr(receipt, key):
            setattr(receipt, key, value)

    # Полная замена позиций — старые удаляем, новые добавляем.
    for old in list(receipt.items):
        db.delete(old)
    db.flush()
    for it in items:
        db.add(models.Item(
            receipt_id=receipt.id,
            name=it.get("name", ""),
            good=it.get("good"),
            brand=it.get("brand"),
            quantity=it.get("quantity"),
            price=it.get("price"),
            category_id=it.get("category_id"),
        ))
    db.commit()
    db.refresh(receipt)
    return receipt


def spending_timeline(db: Session, user_id: int) -> list[dict]:
    """Динамика трат по месяцам (по дате покупки, иначе дате загрузки).

    Агрегируем в Python, чтобы не зависеть от диалекта БД (sqlite/postgres).
    """
    rows = db.execute(
        select(models.Receipt.purchase_date, models.Receipt.created_at, models.Receipt.total)
        .where(models.Receipt.user_id == user_id)
    ).all()
    buckets: dict[str, float] = defaultdict(float)
    for purchase_date, created_at, total in rows:
        if total is None:
            continue
        ref = purchase_date or (created_at.date() if created_at else None)
        if ref is None:
            continue
        buckets[f"{ref.year:04d}-{ref.month:02d}"] += float(total)
    return [{"period": p, "total": buckets[p]} for p in sorted(buckets)]


def top_merchants(db: Session, user_id: int, limit: int = 10) -> list[dict]:
    rows = db.execute(
        select(
            models.Receipt.merchant,
            func.sum(models.Receipt.total),
            func.count(models.Receipt.id),
        )
        .where(models.Receipt.user_id == user_id, models.Receipt.merchant.isnot(None))
        .group_by(models.Receipt.merchant)
        .order_by(func.sum(models.Receipt.total).desc())
        .limit(limit)
    ).all()
    return [
        {"merchant": merchant, "total": float(total or 0), "count": int(count)}
        for merchant, total, count in rows
    ]


def top_goods(db: Session, user_id: int, limit: int = 10) -> list[dict]:
    """Самые частые товары пользователя: считаем по нормализованному названию
    (good, иначе name), сколько раз встречался и на какую сумму."""
    label = func.coalesce(models.Item.good, models.Item.name)
    rows = db.execute(
        select(label, func.count(models.Item.id), func.sum(models.Item.price))
        .join(models.Receipt, models.Receipt.id == models.Item.receipt_id)
        .where(models.Receipt.user_id == user_id, label.isnot(None))
        .group_by(label)
        .order_by(func.count(models.Item.id).desc())
        .limit(limit)
    ).all()
    return [
        {"name": name, "count": int(count), "total": float(total or 0)}
        for name, count, total in rows
    ]


# --------------------------------------------------------------------------
# Бюджеты
# --------------------------------------------------------------------------
def list_budgets(db: Session, user_id: int) -> list[models.Budget]:
    return db.execute(
        select(models.Budget).where(models.Budget.user_id == user_id)
    ).scalars().all()


def create_budget(
    db: Session, user_id: int, limit_amount: Decimal,
    category_id: Optional[int] = None, period: str = "monthly",
) -> models.Budget:
    budget = models.Budget(
        user_id=user_id, category_id=category_id,
        limit_amount=limit_amount, period=period,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, user_id: int, budget_id: int) -> bool:
    budget = db.execute(
        select(models.Budget).where(
            models.Budget.id == budget_id, models.Budget.user_id == user_id
        )
    ).scalar_one_or_none()
    if budget is None:
        return False
    db.delete(budget)
    db.commit()
    return True


# --------------------------------------------------------------------------
# Цели
# --------------------------------------------------------------------------
def list_goals(db: Session, user_id: int) -> list[models.Goal]:
    return db.execute(
        select(models.Goal).where(models.Goal.user_id == user_id)
    ).scalars().all()


def create_goal(
    db: Session, user_id: int, title: str,
    target_amount: Decimal, deadline: Optional[date] = None,
) -> models.Goal:
    goal = models.Goal(
        user_id=user_id, title=title,
        target_amount=target_amount, deadline=deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goal(db: Session, user_id: int, goal_id: int) -> Optional[models.Goal]:
    return db.execute(
        select(models.Goal).where(
            models.Goal.id == goal_id, models.Goal.user_id == user_id
        )
    ).scalar_one_or_none()


def update_goal(db: Session, user_id: int, goal_id: int, fields: dict) -> Optional[models.Goal]:
    goal = get_goal(db, user_id, goal_id)
    if goal is None:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(goal, key):
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user_id: int, goal_id: int) -> bool:
    goal = get_goal(db, user_id, goal_id)
    if goal is None:
        return False
    db.delete(goal)
    db.commit()
    return True


# --------------------------------------------------------------------------
# Сброс пароля
# --------------------------------------------------------------------------
def create_reset_token(db: Session, user_id: int, ttl_minutes: int = 30) -> models.PasswordResetToken:
    token = models.PasswordResetToken(
        user_id=user_id,
        token=secrets.token_urlsafe(32),
        expires_at=_utcnow() + timedelta(minutes=ttl_minutes),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_reset_token(db: Session, token: str) -> Optional[models.PasswordResetToken]:
    obj = db.execute(
        select(models.PasswordResetToken).where(models.PasswordResetToken.token == token)
    ).scalar_one_or_none()
    if obj is None or obj.used:
        return None
    expires_at = obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _utcnow():
        return None
    return obj


def set_user_password(db: Session, user: models.User, password_hash: str) -> None:
    user.password_hash = password_hash
    db.commit()


def consume_reset_token(db: Session, token_obj: models.PasswordResetToken) -> None:
    token_obj.used = True
    db.commit()


# --------------------------------------------------------------------------
# Админка
# --------------------------------------------------------------------------
def list_users(db: Session, limit: int = 100, offset: int = 0) -> list[models.User]:
    return db.execute(
        select(models.User)
        .order_by(models.User.created_at.desc())
        .limit(limit).offset(offset)
    ).scalars().all()


def set_user_active(db: Session, user_id: int, is_active: bool) -> Optional[models.User]:
    user = db.get(models.User, user_id)
    if user is None:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def system_metrics(db: Session) -> dict:
    users_total = db.execute(select(func.count(models.User.id))).scalar() or 0
    users_active = db.execute(
        select(func.count(models.User.id)).where(models.User.is_active.is_(True))
    ).scalar() or 0
    receipts_total = db.execute(select(func.count(models.Receipt.id))).scalar() or 0
    items_total = db.execute(select(func.count(models.Item.id))).scalar() or 0
    needs_review = db.execute(
        select(func.count(models.Receipt.id)).where(models.Receipt.status == "needs_review")
    ).scalar() or 0
    return {
        "users_total": int(users_total),
        "users_active": int(users_active),
        "receipts_total": int(receipts_total),
        "items_total": int(items_total),
        "receipts_needs_review": int(needs_review),
    }