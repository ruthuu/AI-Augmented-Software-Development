"""Exact money handling with Decimal parsing and integer cents. No rounding, no float."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

_AMOUNT_FORMAT = re.compile(r"[+-]?\d+(\.\d+)?")
_MAX_DECIMAL_PLACES = 2


class MoneyError(ValueError):
    """The text is not an amount that can be converted exactly."""


@dataclass(frozen=True)
class AmountAnalysis:
    kind: Literal["empty", "invalid", "valid"]
    is_positive: bool = False
    decimal_places: int = 0
    cents: int | None = None


def analyze_amount_text(text: str | None) -> AmountAnalysis:
    """Parse amount text exactly; cents are set only when there are at most two decimal places."""
    stripped = (text or "").strip()
    if not stripped:
        return AmountAnalysis(kind="empty")
    if _AMOUNT_FORMAT.fullmatch(stripped) is None:
        return AmountAnalysis(kind="invalid")
    value = Decimal(stripped)
    sign, digits, exponent = value.as_tuple()
    places = max(-int(exponent), 0)
    cents = None
    if places <= _MAX_DECIMAL_PLACES:
        magnitude = int("".join(str(d) for d in digits)) * 10 ** (int(exponent) + 2)
        cents = -magnitude if sign else magnitude
    return AmountAnalysis("valid", value > 0, places, cents)


def text_to_cents(text: str) -> int:
    """Convert a positive amount with at most two decimal places to cents; never rounds."""
    result = analyze_amount_text(text)
    if result.kind != "valid" or not result.is_positive or result.cents is None:
        raise MoneyError("not an exact positive amount with at most two decimal places")
    return result.cents


def cents_to_text(cents: int) -> str:
    """Format integer cents as a two-decimal string."""
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{whole}.{fraction:02d}"


def sum_cents(values: Iterable[int]) -> int:
    return sum(values)
