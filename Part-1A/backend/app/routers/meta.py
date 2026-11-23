"""GET /api/config: static lists, limits, and the backend's "today"."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.clock import get_today
from app.core.constants import CATEGORIES, LIMITS, PAYMENT_METHODS
from app.core.money import cents_to_text
from app.schemas.meta import ConfigOut, LimitsOut

router = APIRouter(prefix="/api")


@router.get("/config", response_model=ConfigOut)
def read_config(today: Annotated[date, Depends(get_today)]) -> ConfigOut:
    return ConfigOut(
        today=today.isoformat(),
        currency="INR",
        categories=list(CATEGORIES),
        payment_methods=list(PAYMENT_METHODS),
        limits=LimitsOut(
            max_expense=cents_to_text(LIMITS.max_expense_cents),
            max_budget=cents_to_text(LIMITS.max_budget_cents),
            max_description_length=LIMITS.max_description_length,
            min_date=LIMITS.min_date.isoformat(),
        ),
    )
