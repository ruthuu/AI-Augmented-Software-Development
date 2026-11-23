import os
from typing import Protocol

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.5-flash-lite"
REQUEST_TIMEOUT_MS = 30_000


class LLMUnavailableError(Exception):
    """The model could not be called (missing key, transport or API failure)."""


class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_message: str) -> str: ...


class GeminiClient:
    def __init__(self, sdk_client: genai.Client | None = None) -> None:
        self._sdk_client = sdk_client

    def _client(self) -> genai.Client:
        if self._sdk_client is None:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise LLMUnavailableError("GEMINI_API_KEY is not set")
            self._sdk_client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=REQUEST_TIMEOUT_MS,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        return self._sdk_client

    def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._client()
        model = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""
        except Exception as exc:
            # Only the exception type is kept: SDK messages can echo request details.
            raise LLMUnavailableError(f"Gemini request failed ({type(exc).__name__})") from None
