from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

from app.llm import LLMClient
from app.prompt import SYSTEM_PROMPT, build_user_message
from app.schemas import AgentResult

PAST_TIME_QUESTION = "That date and time is in the past. What future date and time should I use?"


class InvalidOutputError(Exception):
    """The model reply was not a valid AgentResult. It is never repaired."""

    def __init__(self, raw_text: str, detail: str) -> None:
        super().__init__(detail)
        self.raw_text = raw_text
        self.detail = detail


@dataclass(frozen=True)
class AgentOutcome:
    result: AgentResult
    raw_text: str
    past_time_guard_applied: bool


def _summarise(exc: ValidationError) -> str:
    # Locations and messages only: pydantic's `input` field would echo the model text.
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or 'reply'}: {e['msg']}" for e in exc.errors()
    )


def interpret(text: str, now: datetime, client: LLMClient) -> AgentOutcome:
    raw_text = client.generate(SYSTEM_PROMPT, build_user_message(text, now.isoformat()))

    try:
        result = AgentResult.model_validate_json(raw_text)
    except ValidationError as exc:
        raise InvalidOutputError(raw_text, _summarise(exc)) from None

    if result.scheduled_at is not None and result.scheduled_at < now:
        guarded = AgentResult(intent="CLARIFY", clarification=PAST_TIME_QUESTION)
        return AgentOutcome(result=guarded, raw_text=raw_text, past_time_guard_applied=True)

    return AgentOutcome(result=result, raw_text=raw_text, past_time_guard_applied=False)
