class AppError(Exception):
    """Error whose message is safe to show to end users."""

    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, status_code=404, code="not_found")


class ConfigurationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503, code="configuration_error")


class ServiceUnavailableError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503, code="service_unavailable")
