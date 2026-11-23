"""Error body model shared by every non-2xx response."""

from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    errors: list[FieldError]
