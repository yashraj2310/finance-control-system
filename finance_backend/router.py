from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from finance_backend.errors import NotFoundError
from finance_backend.http import Request, normalize_path


Handler = Callable[[Request, Any], Any]


@dataclass(frozen=True)
class Route:
    method: str
    pattern: str
    handler: Handler
    permissions: tuple[str, ...] = ()
    public: bool = False

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if self.method != method:
            return None
        requested = normalize_path(path).strip("/").split("/")
        expected = normalize_path(self.pattern).strip("/").split("/")
        if requested == [""] and expected == [""]:
            return {}
        if len(requested) != len(expected):
            return None
        params: dict[str, str] = {}
        for expected_segment, requested_segment in zip(expected, requested):
            if expected_segment.startswith("{") and expected_segment.endswith("}"):
                params[expected_segment[1:-1]] = requested_segment
                continue
            if expected_segment != requested_segment:
                return None
        return params


class Router:
    def __init__(self) -> None:
        self._routes: list[Route] = []

    def add(
        self,
        method: str,
        pattern: str,
        handler: Handler,
        *,
        permissions: tuple[str, ...] = (),
        public: bool = False,
    ) -> None:
        self._routes.append(
            Route(
                method=method.upper(),
                pattern=normalize_path(pattern),
                handler=handler,
                permissions=permissions,
                public=public,
            )
        )

    def resolve(self, method: str, path: str) -> tuple[Route, dict[str, str]]:
        for route in self._routes:
            params = route.match(method.upper(), path)
            if params is not None:
                return route, params
        raise NotFoundError("The requested endpoint does not exist.")
