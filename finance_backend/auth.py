from __future__ import annotations

import sqlite3
from typing import Any

from finance_backend.errors import ForbiddenError, UnauthorizedError, ValidationError


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {"profile:read", "dashboard:read"},
    "analyst": {"profile:read", "dashboard:read", "records:read"},
    "admin": {
        "profile:read",
        "dashboard:read",
        "records:read",
        "records:write",
        "users:manage",
    },
}


def authenticate_request(
    connection: sqlite3.Connection, headers: dict[str, str]
) -> dict[str, Any]:
    user_id = headers.get("x-user-id")
    if not user_id:
        raise UnauthorizedError(
            "Authentication is required. Provide the X-User-Id header."
        )
    try:
        parsed_user_id = int(user_id)
    except ValueError as exc:
        raise ValidationError("X-User-Id must be an integer.") from exc

    row = connection.execute(
        """
        SELECT id, name, email, role, status, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (parsed_user_id,),
    ).fetchone()
    if row is None:
        raise UnauthorizedError("The requested user could not be authenticated.")

    user = dict(row)
    if user["status"] != "active":
        raise ForbiddenError("Inactive users cannot access the API.")
    return user


def ensure_permissions(user: dict[str, Any], permissions: tuple[str, ...]) -> None:
    allowed = ROLE_PERMISSIONS.get(user["role"], set())
    missing = [permission for permission in permissions if permission not in allowed]
    if missing:
        raise ForbiddenError(
            "This action is not allowed for your role.",
            details={"required_permissions": missing, "role": user["role"]},
        )

