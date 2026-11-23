"""Response models for GET /api/config."""

from pydantic import BaseModel


class LimitsOut(BaseModel):
    max_expense: str
    max_budget: str
    max_description_length: int
    min_date: str


class ConfigOut(BaseModel):
    today: str
    currency: str
    categories: list[str]
    payment_methods: list[str]
    limits: LimitsOut
