import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from customer_support_agent.core.exceptions import AppError

logger = logging.getLogger(__name__)


def error_response(
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    headers: dict[str, str] | None = None,
    details: list[dict] | None = None,
) -> JSONResponse:
    error = {
        "code": code,
        "message": message,
        "retryable": retryable,
        "correlation_id": None,
    }
    if details:
        error["details"] = details
    return JSONResponse(
        status_code=status_code, content={"error": error}, headers=headers
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.retryable)


async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    status = HTTPStatus(exc.status_code)
    return error_response(
        exc.status_code, status.name, status.phrase, headers=exc.headers
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": err["loc"][-1], "issue": err["type"], "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        422, "VALIDATION_ERROR", "The request is invalid.", details=details
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(
        500, "INTERNAL_ERROR", "Something went wrong. Please try again later."
    )


def register_error_handlers(app: FastAPI) -> None:

    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
