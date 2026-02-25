from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Dict, Optional, Union

from .errors import ApiError, SdkError, ValidationError
from .http import HttpClient, UrllibHttpClient


ProgressInput = Union[int, Dict[str, Any], None]


class PingClient:
    def __init__(self, job_key: str, options: Optional[Dict[str, Any]] = None) -> None:
        opts = options or {}
        self._assert_job_key(job_key)

        self.job_key = job_key
        self.base_url = str(opts.get("base_url", "https://cronbeats.io")).rstrip("/")
        self.timeout_ms = int(opts.get("timeout_ms", 5000))
        self.max_retries = int(opts.get("max_retries", 2))
        self.retry_backoff_ms = int(opts.get("retry_backoff_ms", 250))
        self.retry_jitter_ms = int(opts.get("retry_jitter_ms", 100))
        self.user_agent = str(opts.get("user_agent", "cronbeats-python-sdk/0.1.0"))
        self.http_client: HttpClient = opts.get("http_client") or UrllibHttpClient()

    def ping(self) -> Dict[str, Any]:
        return self._request("ping", f"/ping/{self.job_key}")

    def start(self) -> Dict[str, Any]:
        return self._request("start", f"/ping/{self.job_key}/start")

    def end(self, status: str = "success") -> Dict[str, Any]:
        status_value = status.strip().lower()
        if status_value not in ("success", "fail"):
            raise ValidationError('Status must be "success" or "fail".')
        return self._request("end", f"/ping/{self.job_key}/end/{status_value}")

    def success(self) -> Dict[str, Any]:
        return self.end("success")

    def fail(self) -> Dict[str, Any]:
        return self.end("fail")

    def progress(self, seq_or_options: ProgressInput = None, message: Optional[str] = None) -> Dict[str, Any]:
        seq: Optional[int] = None
        msg = message

        if isinstance(seq_or_options, int):
            seq = seq_or_options
        elif isinstance(seq_or_options, dict):
            seq_raw = seq_or_options.get("seq")
            seq = int(seq_raw) if seq_raw is not None else None
            msg = str(seq_or_options.get("message", msg or ""))

        if seq is not None and seq < 0:
            raise ValidationError("Progress seq must be a non-negative integer.")

        safe_msg = str(msg or "")
        if len(safe_msg) > 255:
            safe_msg = safe_msg[:255]

        if seq is not None:
            return self._request(
                "progress",
                f"/ping/{self.job_key}/progress/{seq}",
                {"message": safe_msg},
            )

        body: Dict[str, Any] = {"message": safe_msg}
        if isinstance(seq_or_options, int):
            body["progress"] = seq_or_options

        return self._request("progress", f"/ping/{self.job_key}/progress", body)

    def _request(self, action: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = body or {}
        url = f"{self.base_url}{path}"
        attempt = 0

        try:
            encoded_body = None if len(payload) == 0 else json.dumps(payload, separators=(",", ":"))
        except Exception as exc:
            raise SdkError("Failed to encode request payload.") from exc

        while True:
            try:
                response = self.http_client.request(
                    "POST",
                    url,
                    {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": self.user_agent,
                    },
                    encoded_body,
                    self.timeout_ms,
                )
            except SdkError as exc:
                if attempt >= self.max_retries:
                    raise ApiError(
                        code="NETWORK_ERROR",
                        http_status=None,
                        retryable=True,
                        message=str(exc),
                        raw=exc,
                    ) from exc
                attempt += 1
                self._sleep_with_backoff(attempt)
                continue

            decoded = self._safe_json(response.body)
            status = int(response.status)

            if 200 <= status < 300:
                return self._normalize_success(action, decoded)

            mapped = self._map_error(status)
            if mapped["retryable"] and attempt < self.max_retries:
                attempt += 1
                self._sleep_with_backoff(attempt)
                continue

            raise ApiError(
                code=mapped["code"],
                http_status=status,
                retryable=mapped["retryable"],
                message=str(decoded.get("message", "Request failed")),
                raw=decoded,
            )

    def _normalize_success(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        processing = payload.get("processing_time_ms", 0.0)
        try:
            processing_ms = float(processing)
        except (TypeError, ValueError):
            processing_ms = 0.0

        next_expected = payload.get("next_expected")
        return {
            "ok": True,
            "action": str(payload.get("action", action)),
            "jobKey": str(payload.get("job_key", self.job_key)),
            "timestamp": str(payload.get("timestamp", "")),
            "processingTimeMs": processing_ms,
            "nextExpected": str(next_expected) if next_expected is not None else None,
            "raw": payload,
        }

    def _map_error(self, status: int) -> Dict[str, Any]:
        if status == 400:
            return {"code": "VALIDATION_ERROR", "retryable": False}
        if status == 404:
            return {"code": "NOT_FOUND", "retryable": False}
        if status == 429:
            return {"code": "RATE_LIMITED", "retryable": True}
        if status >= 500:
            return {"code": "SERVER_ERROR", "retryable": True}
        return {"code": "UNKNOWN_ERROR", "retryable": False}

    def _assert_job_key(self, job_key: str) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9]{8}", job_key):
            raise ValidationError("jobKey must be exactly 8 Base62 characters.")

    def _sleep_with_backoff(self, attempt: int) -> None:
        base_ms = self.retry_backoff_ms * (2 ** max(0, attempt - 1))
        jitter_ms = random.randint(0, max(0, self.retry_jitter_ms))
        time.sleep((base_ms + jitter_ms) / 1000.0)

    def _safe_json(self, raw: str) -> Dict[str, Any]:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return decoded
            return {"message": "Invalid JSON response"}
        except json.JSONDecodeError:
            return {"message": "Invalid JSON response"}
