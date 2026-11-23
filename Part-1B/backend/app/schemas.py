import re
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    model_validator,
)

Intent = Literal["CREATE", "RESCHEDULE", "CLARIFY"]

MAX_TEXT_LENGTH = 500

_ISO_START = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def _require_iso_datetime(value: object) -> object:
    # Pydantic would otherwise read 1700000000 or "1700000000" as a Unix timestamp.
    if isinstance(value, datetime) or (isinstance(value, str) and _ISO_START.match(value)):
        return value
    raise ValueError("must be an ISO 8601 date-time string")


IsoDatetime = Annotated[AwareDatetime, BeforeValidator(_require_iso_datetime)]

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
RequestText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXT_LENGTH)
]

# Fields each intent requires; every other optional field must be null.
_REQUIRED: dict[str, set[str]] = {
    "CREATE": {"title", "scheduled_at"},
    "RESCHEDULE": {"reminder_reference", "scheduled_at"},
    "CLARIFY": {"clarification"},
}
_OPTIONAL_FIELDS = {"title", "reminder_reference", "scheduled_at", "clarification"}


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    title: Title | None = None
    reminder_reference: Title | None = None
    scheduled_at: IsoDatetime | None = None
    clarification: Question | None = None

    @model_validator(mode="after")
    def _check_intent_fields(self) -> Self:
        required = _REQUIRED[self.intent]
        missing = sorted(f for f in required if getattr(self, f) is None)
        forbidden = sorted(f for f in _OPTIONAL_FIELDS - required if getattr(self, f) is not None)
        if missing:
            raise ValueError(f"{self.intent} requires: {', '.join(missing)}")
        if forbidden:
            raise ValueError(f"{self.intent} must not set: {', '.join(forbidden)}")
        return self


class InterpretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: RequestText
    now: IsoDatetime


class InterpretResponse(BaseModel):
    result: AgentResult
    persisted: Literal[False] = False
    note: str = "Interpretation only. No reminder was created, updated, stored or scheduled."
