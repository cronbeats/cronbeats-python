from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Dict, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import SdkError


@dataclass
class HttpResponse:
    status: int
    body: str
    headers: Dict[str, str]


class HttpClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        timeout_ms: int,
    ) -> HttpResponse:
        ...


class UrllibHttpClient:
    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        timeout_ms: int,
    ) -> HttpResponse:
        data = body.encode("utf-8") if body is not None else None
        req = Request(url=url, data=data, method=method)
        for key, value in headers.items():
            req.add_header(key, value)

        timeout_seconds = max(1, timeout_ms) / 1000.0
        try:
            with urlopen(req, timeout=timeout_seconds) as res:
                text = res.read().decode("utf-8")
                response_headers = {k.lower(): v for k, v in res.headers.items()}
                return HttpResponse(status=res.status, body=text, headers=response_headers)
        except HTTPError as exc:
            error_text = exc.read().decode("utf-8") if exc.fp else ""
            error_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return HttpResponse(status=exc.code, body=error_text, headers=error_headers)
        except (URLError, socket.timeout, TimeoutError, OSError) as exc:
            raise SdkError(str(exc)) from exc
