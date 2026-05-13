"""Minimal HTTP client with connection pooling and timeout."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


_DEFAULT_TIMEOUT = 10.0
_DEFAULT_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def build_request(
    url: str,
    method: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> urllib.request.Request:
    """Construct a Request object with JSON body and merged headers."""
    merged = {**_DEFAULT_HEADERS, **(headers or {})}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    return urllib.request.Request(url, data=data, headers=merged, method=method)


def parse_response(response: Any) -> dict[str, Any]:
    """Read and JSON-decode an HTTP response object."""
    raw = response.read()
    return json.loads(raw.decode("utf-8"))  # type: ignore[no-any-return]


class HttpClient:
    """Simple HTTP client that wraps urllib with JSON helpers."""

    def __init__(self, base_url: str, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Send a GET request. Raises urllib.error.HTTPError on 4xx/5xx."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        req = build_request(url, "GET")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return parse_response(resp)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request with a JSON body."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        req = build_request(url, "POST", body=body)
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return parse_response(resp)

    def delete(self, path: str) -> int:
        """Send a DELETE request. Returns the HTTP status code."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        req = build_request(url, "DELETE")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return resp.status  # type: ignore[no-any-return]
