"""Response model for GET /api/summary."""

from pydantic import BaseModel

from app.schemas.budget import BudgetBrief


class CategoryTotalOut(BaseModel):
    category: str
    total: str
    count: int


class SummaryOut(BaseModel):
    month: str
    total_spent: str
    expense_count: int
    total_recorded_count: int
    by_category: list[CategoryTotalOut]
    budget: BudgetBrief | None
    remaining: str | None
    over_budget: bool
    over_budget_by: str | None
