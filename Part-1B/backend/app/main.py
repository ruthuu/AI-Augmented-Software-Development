from functools import lru_cache
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent import InvalidOutputError, interpret
from app.llm import GeminiClient, LLMClient, LLMUnavailableError
from app.schemas import InterpretRequest, InterpretResponse

# Reads backend/.env into the process environment; values are never logged or returned.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(title="Reminder Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache
def get_llm_client() -> LLMClient:
    return GeminiClient()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def _invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Field names and messages only: pydantic's `input` would echo what the user sent.
    parts = [
        f"{'.'.join(str(p) for p in e['loc'] if p != 'body') or 'body'}: {e['msg']}"
        for e in exc.errors()
    ]
    return _error(422, "invalid_request", "; ".join(parts))


@app.exception_handler(LLMUnavailableError)
async def _llm_unavailable(_: Request, __: LLMUnavailableError) -> JSONResponse:
    return _error(
        502, "llm_unavailable", "The language model could not be reached. Try again later."
    )


@app.exception_handler(InvalidOutputError)
async def _llm_invalid_output(_: Request, __: InvalidOutputError) -> JSONResponse:
    return _error(
        502,
        "llm_invalid_output",
        "The model returned a reply that does not match the required format.",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/interpret", response_model=InterpretResponse)
def interpret_request(
    request: InterpretRequest, client: Annotated[LLMClient, Depends(get_llm_client)]
) -> InterpretResponse:
    outcome = interpret(request.text, request.now, client)
    return InterpretResponse(result=outcome.result)
