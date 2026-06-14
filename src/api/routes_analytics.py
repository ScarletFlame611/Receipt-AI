"""Роуты аналитики: сводка трат, разбивка по категориям, динамика, топ
магазинов, а также бюджеты и цели. Всё изолировано по user_id."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import CurrentUser, get_db
from src.db import crud, schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.SpendingSummary)
def spending_summary(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return schemas.SpendingSummary(
        total=crud.spending_total(db, current_user.id),
        receipts_count=crud.receipts_count(db, current_user.id),
        by_category=crud.summary_by_category(db, current_user.id),
    )


@router.get("/by-category", response_model=list[schemas.CategorySpending])
def by_category(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return crud.summary_by_category(db, current_user.id)


@router.get("/timeline", response_model=list[schemas.TimePoint])
def timeline(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return crud.spending_timeline(db, current_user.id)


@router.get("/top-merchants", response_model=list[schemas.MerchantStat])
def top_merchants(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 10,
):
    return crud.top_merchants(db, current_user.id, limit=limit)


@router.get("/top-goods", response_model=list[schemas.GoodStat])
def top_goods(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 10,
):
    return crud.top_goods(db, current_user.id, limit=limit)


# --------------------------------------------------------------------------
# Бюджеты
# --------------------------------------------------------------------------
@router.get("/budgets", response_model=list[schemas.BudgetOut])
def list_budgets(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return crud.list_budgets(db, current_user.id)


@router.post("/budgets", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: schemas.BudgetCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    return crud.create_budget(
        db, current_user.id,
        limit_amount=payload.limit_amount,
        category_id=payload.category_id,
        period=payload.period,
    )


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    if not crud.delete_budget(db, current_user.id, budget_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бюджет не найден")
    return None


# --------------------------------------------------------------------------
# Цели
# --------------------------------------------------------------------------
@router.get("/goals", response_model=list[schemas.GoalOut])
def list_goals(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return crud.list_goals(db, current_user.id)


@router.post("/goals", response_model=schemas.GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: schemas.GoalCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    return crud.create_goal(
        db, current_user.id,
        title=payload.title,
        target_amount=payload.target_amount,
        deadline=payload.deadline,
    )


@router.put("/goals/{goal_id}", response_model=schemas.GoalOut)
def update_goal(
    goal_id: int,
    payload: schemas.GoalUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    goal = crud.update_goal(
        db, current_user.id, goal_id, payload.model_dump(exclude_unset=True)
    )
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Цель не найдена")
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    if not crud.delete_goal(db, current_user.id, goal_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Цель не найдена")
    return None
