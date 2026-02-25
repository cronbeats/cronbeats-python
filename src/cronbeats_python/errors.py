from __future__ import annotations

from typing import Any, Optional


class SdkError(Exception):
    pass


class ValidationError(SdkError):
    pass


class ApiError(SdkError):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: Optional[int] = None,
        retryable: bool = False,
        raw: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retryable = retryable
        self.raw = raw
