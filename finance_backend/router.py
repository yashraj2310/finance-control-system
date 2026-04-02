from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from finance_backend.errors import MethodNotAllowedError, NotFoundError
from finance_backend.http import Request, normalize_path


Handler = Callable[[Request, Any], Any]


@dataclass(frozen=True)
class Route:
    method: str
    pattern: str
    handler: Handler
    permissions: tuple[str, ...] = ()
    public: bool = False

    def match_path(self, path: str) -> dict[str, str] | None:
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

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if self.method != method:
            return None
        return self.match_path(path)


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
        allowed_methods: list[str] = []
        for route in self._routes:
            path_params = route.match_path(path)
            if path_params is None:
                continue
            allowed_methods.append(route.method)
            if route.method != method.upper():
                continue
            params = route.match(method.upper(), path)
            if params is not None:
                return route, params
        if allowed_methods:
            raise MethodNotAllowedError(
                "The requested HTTP method is not supported for this endpoint.",
                allowed_methods=sorted(set(allowed_methods)),
            )
        raise NotFoundError("The requested endpoint does not exist.")
