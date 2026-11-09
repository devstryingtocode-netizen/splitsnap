from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    location: list[str | int]
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ValidationErrorBody(ErrorBody):
    details: list[dict[str, Any]]
