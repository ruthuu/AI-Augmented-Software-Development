"""Domain errors and the handlers that turn every failure into the single error body."""

import logging
from collections.abc import Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorBody, FieldError

logger = logging.getLogger("spendwise")

VALIDATION_MESSAGE = "Please correct the highlighted fields."
NOT_FOUND_MESSAGE = "This expense no longer exists"
GENERIC_500_MESSAGE = "Something went wrong on the server. Please try again."
BODY_MESSAGE = "Request body must be valid JSON"
UNKNOWN_FIELD_MESSAGE = "Unknown field"

# Used only for request shapes the parsers never see (for example a JSON number).
_SHAPE_FALLBACK = {
    "amount": "Enter a valid amount",
    "description": "Description is required",
    "category": "Select a valid category",
    "payment_method": "Select a valid payment method",
    "expense_date": "Enter a valid date",
    "month": "Enter a valid month",
}


class ValidationFailure(Exception):
    def __init__(self, errors: Sequence[tuple[str, str]]) -> None:
        super().__init__("validation failed")
        self.errors = [FieldError(field=field, message=message) for field, message in errors]


class NotFound(Exception):
    def __init__(self, message: str = NOT_FOUND_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


def _respond(status: int, code: str, message: str, errors: list[FieldError]) -> JSONResponse:
    body = ErrorBody(code=code, message=message, errors=errors)
    return JSONResponse(status_code=status, content=body.model_dump())


def _shape_errors(raw_errors: Sequence[object]) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for item in raw_errors:
        entry = item if isinstance(item, dict) else {}
        loc = tuple(entry.get("loc", ()))
        kind = str(entry.get("type", ""))
        if kind == "json_invalid" or loc == ("body",):
            found.setdefault("body", BODY_MESSAGE)
        elif kind == "extra_forbidden":
            found.setdefault(str(loc[-1]), UNKNOWN_FIELD_MESSAGE)
        elif len(loc) >= 2:
            field = str(loc[1])
            found.setdefault(field, _SHAPE_FALLBACK.get(field, BODY_MESSAGE))
        else:
            found.setdefault("body", BODY_MESSAGE)
    return list(found.items())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationFailure)
    async def _validation_failure(_: Request, exc: ValidationFailure) -> JSONResponse:
        return _respond(422, "validation_error", VALIDATION_MESSAGE, exc.errors)

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return _respond(404, "not_found", exc.message, [])

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        raw = exc.errors()
        if any(tuple(e.get("loc", ()))[:1] == ("path",) for e in raw):
            return _respond(404, "not_found", NOT_FOUND_MESSAGE, [])
        errors = [FieldError(field=f, message=m) for f, m in _shape_errors(raw)]
        return _respond(422, "validation_error", VALIDATION_MESSAGE, errors)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _respond(404, "not_found", "Not found", [])
        return _respond(exc.status_code, "http_error", "The request could not be processed", [])

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error", exc_info=exc)
        return _respond(500, "internal_error", GENERIC_500_MESSAGE, [])
