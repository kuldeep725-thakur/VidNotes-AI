class AppError(Exception):
    """An error whose message is safe and useful to show to the user."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ExternalServiceError(AppError):
    """A failure while talking to Supadata or Gemini."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code)
