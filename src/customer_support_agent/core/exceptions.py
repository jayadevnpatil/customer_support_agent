class AppError(Exception):
    """Base class for errors returned to the client in the standard error shape."""

    code = "INTERNAL_ERROR"
    status_code = 500
    message = "Something went wrong. Please try again later."
    retryable = False

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NotFoundAppError(AppError):
    """Raised when requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404
    message = "Resource not found."


class NotImplementedAppError(AppError):
    """Raised when requested application feature is not implemented."""

    code = "NOT_IMPLEMENTED"
    status_code = 501
    message = "Feature not implemented."
