"""The backend's idea of "today" (FR-041); one source for validation, config, and the dashboard."""

from datetime import date

from app.core.config import Settings


def get_today() -> date:
    """Local date of the machine, or SPENDWISE_TODAY when set. Overridden in tests."""
    return Settings.from_env().today or date.today()
