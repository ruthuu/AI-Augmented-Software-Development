from types import SimpleNamespace

import pytest

from app import llm
from app.llm import GeminiClient, LLMUnavailableError
from app.schemas import AgentResult
from tests.support import FakeLLMClient, unavailable

SECRET = "sk-test-secret-123"  # noqa: S105 - dummy value used to prove nothing leaks


class StubModels:
    """Stands in for the SDK's `models` object; no network."""

    def __init__(self, text: str | None = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


def stub_sdk(models: StubModels) -> SimpleNamespace:
    return SimpleNamespace(models=models)


# --- FakeLLMClient -------------------------------------------------------------------------


def test_fake_returns_reply_and_records_the_call() -> None:
    fake = FakeLLMClient(reply='{"intent":"CLARIFY","clarification":"When?"}')
    out = fake.generate("system", "user")
    assert out == '{"intent":"CLARIFY","clarification":"When?"}'
    assert fake.calls == [("system", "user")]


def test_fake_raises_configured_api_error() -> None:
    fake = FakeLLMClient(error=unavailable())
    with pytest.raises(LLMUnavailableError):
        fake.generate("s", "u")
    assert len(fake.calls) == 1


def test_fake_invalid_json_is_returned_unchanged_and_rejected_by_the_schema() -> None:
    fake = FakeLLMClient(reply="Sure! Here is your reminder")
    raw = fake.generate("s", "u")
    assert raw == "Sure! Here is your reminder"
    with pytest.raises(ValueError):
        AgentResult.model_validate_json(raw)


# --- GeminiClient (SDK stubbed, no network) --------------------------------------------------


def test_gemini_success_makes_exactly_one_call_with_expected_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    models = StubModels(text='{"intent":"CLARIFY","clarification":"When?"}')
    client = GeminiClient(sdk_client=stub_sdk(models))

    out = client.generate("SYSTEM", "USER")

    assert out == '{"intent":"CLARIFY","clarification":"When?"}'
    assert len(models.calls) == 1
    call = models.calls[0]
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["contents"] == "USER"
    config = call["config"]
    assert config.system_instruction == "SYSTEM"
    assert config.temperature == 0
    assert config.response_mime_type == "application/json"


def test_gemini_model_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "some-other-model")
    models = StubModels(text="{}")
    GeminiClient(sdk_client=stub_sdk(models)).generate("s", "u")
    assert models.calls[0]["model"] == "some-other-model"


def test_gemini_missing_api_key_fails_before_any_sdk_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def boom(**_: object) -> None:
        raise AssertionError("SDK client must not be created without a key")

    monkeypatch.setattr(llm.genai, "Client", boom)
    with pytest.raises(LLMUnavailableError, match="GEMINI_API_KEY"):
        GeminiClient().generate("s", "u")


def test_gemini_blank_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    with pytest.raises(LLMUnavailableError, match="GEMINI_API_KEY"):
        GeminiClient().generate("s", "u")


def test_gemini_key_is_read_from_environment_and_retries_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    created: list[dict[str, object]] = []
    models = StubModels(text="{}")

    def fake_client(**kwargs: object) -> SimpleNamespace:
        created.append(kwargs)
        return stub_sdk(models)

    monkeypatch.setattr(llm.genai, "Client", fake_client)
    GeminiClient().generate("s", "u")

    assert len(created) == 1
    assert created[0]["api_key"] == SECRET
    assert created[0]["http_options"].retry_options.attempts == 1
    assert len(models.calls) == 1


def test_gemini_api_error_is_wrapped_without_leaking_details_and_not_retried() -> None:
    models = StubModels(error=RuntimeError(f"401 for key {SECRET}"))
    client = GeminiClient(sdk_client=stub_sdk(models))

    with pytest.raises(LLMUnavailableError) as info:
        client.generate("s", "u")

    assert len(models.calls) == 1
    assert SECRET not in str(info.value)
    assert "RuntimeError" in str(info.value)
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__ is True


@pytest.mark.parametrize("text", [None, ""])
def test_gemini_empty_reply_is_returned_as_empty_string(text: str | None) -> None:
    client = GeminiClient(sdk_client=stub_sdk(StubModels(text=text)))
    assert client.generate("s", "u") == ""


def test_gemini_invalid_json_reply_is_passed_through_unchanged() -> None:
    client = GeminiClient(sdk_client=stub_sdk(StubModels(text="not json at all")))
    assert client.generate("s", "u") == "not json at all"
