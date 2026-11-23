from app.llm import LLMUnavailableError


class FakeLLMClient:
    """In-memory stand-in for the model; records every call it receives."""

    def __init__(self, reply: str = "", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        if self.error is not None:
            raise self.error
        return self.reply


def unavailable() -> LLMUnavailableError:
    return LLMUnavailableError("Gemini request failed (FakeError)")
