import json
from typing import Dict, List, Optional

import pytest

from cronbeats_python import ApiError, PingClient, SdkError, ValidationError
from cronbeats_python.http import HttpResponse


class StubHttpClient:
    def __init__(self, responses: Optional[List[HttpResponse]] = None, network_failures: int = 0) -> None:
        self.responses = responses or []
        self.network_failures = network_failures
        self.calls: List[Dict[str, Optional[str]]] = []

    def request(self, method, url, headers, body, timeout_ms):  # noqa: ANN001
        self.calls.append({"method": method, "url": url, "body": body})
        if self.network_failures > 0:
            self.network_failures -= 1
            raise SdkError("socket timeout")
        if not self.responses:
            return HttpResponse(status=200, body=json.dumps({}), headers={})
        return self.responses.pop(0)


def test_invalid_job_key_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        PingClient("invalid-key")


def test_success_response_is_normalized() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(
                status=200,
                body=json.dumps(
                    {
                        "status": "success",
                        "message": "OK",
                        "action": "ping",
                        "job_key": "abc123de",
                        "timestamp": "2026-02-25 12:00:00",
                        "processing_time_ms": 8.25,
                    }
                ),
                headers={},
            )
        ]
    )
    client = PingClient("abc123de", {"http_client": stub})
    res = client.ping()
    assert res["ok"] is True
    assert res["action"] == "ping"
    assert res["jobKey"] == "abc123de"
    assert res["processingTimeMs"] == 8.25


def test_404_maps_to_not_found() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(status=404, body=json.dumps({"status": "error", "message": "Job not found"}), headers={})
        ]
    )
    client = PingClient("abc123de", {"http_client": stub, "max_retries": 0})
    with pytest.raises(ApiError) as exc:
        client.ping()
    assert exc.value.code == "NOT_FOUND"
    assert exc.value.retryable is False
    assert exc.value.http_status == 404


def test_retry_on_429_then_success() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(
                status=429,
                body=json.dumps({"status": "error", "message": "Too many requests"}),
                headers={},
            ),
            HttpResponse(
                status=200,
                body=json.dumps(
                    {
                        "status": "success",
                        "message": "OK",
                        "action": "ping",
                        "job_key": "abc123de",
                        "timestamp": "2026-02-25 12:00:00",
                        "processing_time_ms": 7.1,
                    }
                ),
                headers={},
            ),
        ]
    )
    client = PingClient(
        "abc123de",
        {
            "http_client": stub,
            "max_retries": 2,
            "retry_backoff_ms": 1,
            "retry_jitter_ms": 0,
        },
    )
    res = client.ping()
    assert res["ok"] is True
    assert len(stub.calls) == 2


def test_no_retry_on_400() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(status=400, body=json.dumps({"status": "error", "message": "Invalid request"}), headers={})
        ]
    )
    client = PingClient("abc123de", {"http_client": stub, "max_retries": 2})
    with pytest.raises(ApiError) as exc:
        client.ping()
    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.retryable is False
    assert len(stub.calls) == 1


def test_retry_on_network_error_then_success() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(
                status=200,
                body=json.dumps(
                    {
                        "status": "success",
                        "message": "OK",
                        "action": "ping",
                        "job_key": "abc123de",
                        "timestamp": "2026-02-25 12:00:00",
                        "processing_time_ms": 3.3,
                    }
                ),
                headers={},
            )
        ],
        network_failures=1,
    )
    client = PingClient(
        "abc123de",
        {
            "http_client": stub,
            "max_retries": 2,
            "retry_backoff_ms": 1,
            "retry_jitter_ms": 0,
        },
    )
    result = client.ping()
    assert result["ok"] is True
    assert len(stub.calls) == 2


def test_progress_normalization_and_message_truncation() -> None:
    stub = StubHttpClient(
        responses=[
            HttpResponse(
                status=200,
                body=json.dumps(
                    {
                        "status": "success",
                        "message": "OK",
                        "action": "progress",
                        "job_key": "abc123de",
                        "timestamp": "2026-02-25 12:00:00",
                        "processing_time_ms": 8,
                    }
                ),
                headers={},
            )
        ]
    )
    long_msg = "x" * 300
    client = PingClient("abc123de", {"http_client": stub})
    client.progress({"seq": 50, "message": long_msg})
    assert stub.calls[0]["url"].endswith("/ping/abc123de/progress/50")
    sent = json.loads(stub.calls[0]["body"] or "{}")
    assert len(sent["message"]) == 255
