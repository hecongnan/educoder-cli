class EduCoderAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SignatureError(EduCoderAPIError):
    pass


class SessionExpiredError(EduCoderAPIError):
    pass


class EvaluationTimeoutError(EduCoderAPIError):
    pass
