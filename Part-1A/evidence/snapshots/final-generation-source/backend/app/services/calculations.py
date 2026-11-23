"""Pure calculations in integer cents."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetStatus:
    remaining_cents: int | None
    over_budget: bool
    over_budget_by_cents: int | None


@dataclass(frozen=True)
class CategoryTotal:
    category: str
    total_cents: int
    count: int


def budget_status(spent_cents: int, budget_cents: int | None) -> BudgetStatus:
    """Remaining never goes below zero; an overage is reported separately (FR-025, FR-026)."""
    if budget_cents is None:
        return BudgetStatus(remaining_cents=None, over_budget=False, over_budget_by_cents=None)
    if spent_cents > budget_cents:
        return BudgetStatus(0, True, spent_cents - budget_cents)
    return BudgetStatus(budget_cents - spent_cents, False, None)


def summarize_by_category(rows: Iterable[tuple[str, int]]) -> list[CategoryTotal]:
    """Integer sums per category, highest total first, then by category name (FR-031)."""
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    for category, cents in rows:
        totals[category] = totals.get(category, 0) + cents
        counts[category] = counts.get(category, 0) + 1
    ordered = sorted(totals, key=lambda name: (-totals[name], name))
    return [CategoryTotal(name, totals[name], counts[name]) for name in ordered]
