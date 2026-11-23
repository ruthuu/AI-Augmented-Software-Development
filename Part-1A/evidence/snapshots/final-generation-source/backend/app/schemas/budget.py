"""Budget request and response models."""

from pydantic import BaseModel, ConfigDict


class BudgetIn(BaseModel):
    """Shape only: unknown fields are refused; the amount rules live in services/validation.py."""

    model_config = ConfigDict(extra="forbid", strict=True)

    amount: str | None = None


class BudgetOut(BaseModel):
    month: str
    amount: str
    updated_at: str


class BudgetBrief(BaseModel):
    month: str
    amount: str
