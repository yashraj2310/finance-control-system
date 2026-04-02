from __future__ import annotations

import json
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from finance_backend.errors import ValidationError


_UNSET = object()


def normalize_path(path: str) -> str:
    if not path:
        return "/"
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: bytes
    path_params: dict[str, str] = field(default_factory=dict)
    current_user: dict[str, Any] | None = None
    _json_cache: Any = field(default=_UNSET, init=False, repr=False)

    @classmethod
    def from_environ(cls, environ: dict[str, Any]) -> "Request":
        content_length = environ.get("CONTENT_LENGTH") or "0"
        try:
            length = int(content_length)
        except ValueError:
            length = 0
        body = environ["wsgi.input"].read(length) if length > 0 else b""
        headers: dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
        if environ.get("CONTENT_TYPE"):
            headers["content-type"] = environ["CONTENT_TYPE"]
        return cls(
            method=environ["REQUEST_METHOD"].upper(),
            path=normalize_path(environ.get("PATH_INFO", "/")),
            query=parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=False),
            headers=headers,
            body=body,
        )

    def json(self) -> dict[str, Any]:
        if self._json_cache is _UNSET:
            if not self.body:
                raise ValidationError("A JSON request body is required.")
            try:
                payload = json.loads(self.body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    "Request body must contain valid JSON.",
                    details={"position": exc.pos},
                ) from exc
            if not isinstance(payload, dict):
                raise ValidationError("JSON request bodies must be objects.")
            self._json_cache = payload
        return self._json_cache

    def query_value(self, key: str, default: str | None = None) -> str | None:
        values = self.query.get(key)
        if not values:
            return default
        return values[-1]


@dataclass
class Response:
    status_code: int = 200
    payload: Any = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_wsgi(self, start_response: Any) -> list[bytes]:
        body = b""
        response_headers = dict(self.headers)
        if self.payload is not None:
            body = json.dumps(self.payload, separators=(",", ":")).encode("utf-8")
            response_headers.setdefault("Content-Type", "application/json; charset=utf-8")
        response_headers["Content-Length"] = str(len(body))
        status_text = f"{self.status_code} {HTTPStatus(self.status_code).phrase}"
        start_response(status_text, list(response_headers.items()))
        return [body]
