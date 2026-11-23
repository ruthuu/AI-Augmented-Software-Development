"""T017: exact money parsing and conversion (no rounding, integer cents)."""

import pytest

from app.core import money
from app.core.constants import LIMITS


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("0.01", 1),
        ("12", 1200),
        ("12.5", 1250),
        ("12.50", 1250),
        ("999999.99", 99999999),
        ("9999999.99", 999999999),
    ],
)
def test_text_to_cents_is_exact(text: str, cents: int) -> None:
    assert money.text_to_cents(text) == cents


@pytest.mark.parametrize(
    ("cents", "text"),
    [
        (1, "0.01"),
        (1200, "12.00"),
        (1250, "12.50"),
        (99999999, "999999.99"),
        (999999999, "9999999.99"),
        (9999999999, "99999999.99"),
        (0, "0.00"),
        (7, "0.07"),
    ],
)
def test_cents_to_text_has_two_decimals(cents: int, text: str) -> None:
    assert money.cents_to_text(cents) == text


@pytest.mark.parametrize("text", ["0.01", "12", "12.5", "12.50", "999999.99", "9999999.99"])
def test_round_trip(text: str) -> None:
    cents = money.text_to_cents(text)
    assert money.text_to_cents(money.cents_to_text(cents)) == cents


def test_sum_of_cents_is_exact_for_point_ten_plus_point_twenty() -> None:
    total = money.sum_cents([money.text_to_cents("0.10"), money.text_to_cents("0.20")])
    assert total == 30
    assert money.cents_to_text(total) == "0.30"


def test_sum_of_many_small_amounts_has_no_drift() -> None:
    total = money.sum_cents(money.text_to_cents("0.10") for _ in range(1000))
    assert money.cents_to_text(total) == "100.00"


def test_limits_are_exact_integer_cents() -> None:
    assert money.text_to_cents("9999999.99") == 999999999 == LIMITS.max_expense_cents
    assert money.text_to_cents("99999999.99") == 9999999999 == LIMITS.max_budget_cents
    assert money.text_to_cents("0.01") == LIMITS.min_amount_cents == 1


@pytest.mark.parametrize("text", ["0.005", "12.345", "12.999", "12.500", "0.001", "1.0001"])
def test_more_than_two_decimals_is_never_converted_or_rounded(text: str) -> None:
    with pytest.raises(money.MoneyError):
        money.text_to_cents(text)


@pytest.mark.parametrize("text", ["", "   ", "abc", "12.", ".5", "1,000", "1e3", "0", "-5"])
def test_text_to_cents_rejects_non_amounts(text: str) -> None:
    with pytest.raises(money.MoneyError):
        money.text_to_cents(text)


@pytest.mark.parametrize("text", ["", "   ", "\t"])
def test_analyze_reports_empty(text: str) -> None:
    assert money.analyze_amount_text(text).kind == "empty"


def test_analyze_treats_none_as_empty() -> None:
    assert money.analyze_amount_text(None).kind == "empty"


@pytest.mark.parametrize("text", ["abc", "12.", ".5", "1,000", "1e3", "12abc", "--5", "1 2"])
def test_analyze_reports_invalid_format(text: str) -> None:
    assert money.analyze_amount_text(text).kind == "invalid"


def test_analyze_whole_number() -> None:
    result = money.analyze_amount_text("12")
    assert (result.kind, result.is_positive, result.decimal_places, result.cents) == (
        "valid",
        True,
        0,
        1200,
    )


def test_analyze_two_decimals() -> None:
    result = money.analyze_amount_text("12.50")
    assert (result.kind, result.is_positive, result.decimal_places, result.cents) == (
        "valid",
        True,
        2,
        1250,
    )


@pytest.mark.parametrize("text", ["12.345", "12.500", "0.005"])
def test_analyze_three_decimals_has_no_cents(text: str) -> None:
    result = money.analyze_amount_text(text)
    assert result.kind == "valid"
    assert result.decimal_places == 3
    assert result.cents is None


@pytest.mark.parametrize("text", ["0", "0.00", "-5", "-0.01"])
def test_analyze_non_positive(text: str) -> None:
    result = money.analyze_amount_text(text)
    assert result.kind == "valid"
    assert result.is_positive is False


def test_analyze_trims_surrounding_whitespace() -> None:
    assert money.analyze_amount_text("  12.50  ").cents == 1250


def test_analyze_is_exact_for_very_long_numbers() -> None:
    result = money.analyze_amount_text("99999999999999999999.99")
    assert result.kind == "valid"
    assert result.cents == 9999999999999999999999


def test_analyze_does_not_round_at_the_boundary() -> None:
    result = money.analyze_amount_text("9999999.995")
    assert result.decimal_places == 3
    assert result.cents is None
