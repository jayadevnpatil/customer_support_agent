from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from customer_support_agent.core.exceptions import AppError


def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
                "correlation_id": None,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:

    app.add_exception_handler(AppError, handle_app_error)
