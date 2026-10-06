"""API adapter layer: maps domain errors to HTTP responses, in one place."""

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hotel.domain.errors import (
    BookingNotFound,
    DomainError,
    InvalidStayPeriod,
    RoomNotFound,
    RoomUnavailable,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    RoomNotFound: 404,
    BookingNotFound: 404,
    RoomUnavailable: 409,
    InvalidStayPeriod: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _json_error(status_code))


def _json_error(status_code: int) -> Callable[[Request, Exception], JSONResponse]:
    def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler
