"""Monthly summary use case."""

import sqlite3
from datetime import date

from app.core.money import cents_to_text, sum_cents
from app.repositories import budget_repository, expense_repository
from app.schemas.budget import BudgetBrief
from app.schemas.summary import CategoryTotalOut, SummaryOut
from app.services import validation
from app.services.calculations import budget_status, summarize_by_category


def summarize(conn: sqlite3.Connection, month: str | None, today: date) -> SummaryOut:
    chosen = validation.parse_month(month) if month else today.strftime("%Y-%m")
    first_day, last_day = validation.month_range(chosen)
    rows = expense_repository.month_rows(conn, first_day, last_day)
    total_cents = sum_cents(cents for _, cents in rows)
    budget_cents = budget_repository.get_cents(conn, chosen)
    status = budget_status(total_cents, budget_cents)
    return SummaryOut(
        month=chosen,
        total_spent=cents_to_text(total_cents),
        expense_count=len(rows),
        total_recorded_count=expense_repository.count_all(conn),
        by_category=[
            CategoryTotalOut(
                category=item.category, total=cents_to_text(item.total_cents), count=item.count
            )
            for item in summarize_by_category(rows)
        ],
        budget=None
        if budget_cents is None
        else BudgetBrief(month=chosen, amount=cents_to_text(budget_cents)),
        remaining=None if status.remaining_cents is None else cents_to_text(status.remaining_cents),
        over_budget=status.over_budget,
        over_budget_by=None
        if status.over_budget_by_cents is None
        else cents_to_text(status.over_budget_by_cents),
    )
