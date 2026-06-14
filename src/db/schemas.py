from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    is_admin: bool
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageOut(BaseModel):
    """Простой ответ-подтверждение для действий без полезной нагрузки."""
    detail: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    color: Optional[str] = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    good: Optional[str] = None
    brand: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    category_id: Optional[int] = None


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant: Optional[str] = None
    purchase_date: Optional[date] = None
    total: Optional[Decimal] = None
    receipt_type: Optional[str] = None
    language: Optional[str] = None
    status: str
    created_at: datetime
    items: list[ItemOut] = []


class ReceiptUpdate(BaseModel):
    merchant: Optional[str] = None
    purchase_date: Optional[date] = None
    total: Optional[Decimal] = None
    receipt_type: Optional[str] = None


class ItemIn(BaseModel):
    """Позиция чека при ручной правке."""
    name: str
    good: Optional[str] = None
    brand: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    category_id: Optional[int] = None


class ReceiptReview(BaseModel):
    """Ручная правка чека: поля шапки + полная замена списка позиций.

    Пользователь подтверждает/исправляет распознанное; статус по умолчанию
    переводится в ``ok``, но его можно задать явно.
    """
    merchant: Optional[str] = None
    purchase_date: Optional[date] = None
    total: Optional[Decimal] = None
    receipt_type: Optional[str] = None
    status: str = "ok"
    items: list[ItemIn] = []


class BudgetCreate(BaseModel):
    category_id: Optional[int] = None
    limit_amount: Decimal
    period: str = "monthly"


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: Optional[int] = None
    limit_amount: Decimal
    period: str


class GoalCreate(BaseModel):
    title: str
    target_amount: Decimal
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    deadline: Optional[date] = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[date] = None


# --------------------------------------------------------------------------
# Аналитика
# --------------------------------------------------------------------------
class CategorySpending(BaseModel):
    category: Optional[str] = None
    total: float


class TimePoint(BaseModel):
    period: str  # 'YYYY-MM'
    total: float


class MerchantStat(BaseModel):
    merchant: Optional[str] = None
    total: float
    count: int


class GoodStat(BaseModel):
    name: Optional[str] = None
    count: int
    total: float


class SpendingSummary(BaseModel):
    total: float
    receipts_count: int = 0
    by_category: list[CategorySpending]


# --------------------------------------------------------------------------
# Админка
# --------------------------------------------------------------------------
class SystemMetrics(BaseModel):
    users_total: int
    users_active: int
    receipts_total: int
    items_total: int
    receipts_needs_review: int