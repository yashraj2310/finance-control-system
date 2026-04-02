from __future__ import annotations

import sqlite3
from typing import Any

from finance_backend.auth import authenticate_request, ensure_permissions
from finance_backend.config import AppConfig
from finance_backend.database import get_connection, initialize_database
from finance_backend.errors import AppError, ValidationError
from finance_backend.http import Request, Response
from finance_backend.router import Router
from finance_backend.services import DashboardService, RecordService, UserService
from finance_backend.validation import (
    require_int,
    validate_record_filters,
    validate_record_payload,
    validate_summary_filters,
    validate_user_payload,
)


def create_app(config: AppConfig):
    initialize_database(
        config.database_path, seed_demo_records=config.seed_demo_records
    )
    router = _build_router()

    def application(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        request = Request.from_environ(environ)
        try:
            route, path_params = router.resolve(request.method, request.path)
            request.path_params = path_params
            connection = get_connection(config.database_path)
            try:
                if not route.public:
                    request.current_user = authenticate_request(connection, request.headers)
                    ensure_permissions(request.current_user, route.permissions)
                response = route.handler(request, connection)
                connection.commit()
            finally:
                connection.close()
        except AppError as exc:
            response = Response(status_code=exc.status_code, payload=exc.to_dict())
        except sqlite3.Error:
            response = Response(
                status_code=500,
                payload={
                    "error": {
                        "code": "database_error",
                        "message": "The database operation could not be completed.",
                    }
                },
            )
        except Exception:
            response = Response(
                status_code=500,
                payload={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected server error occurred.",
                    }
                },
            )
        return response.to_wsgi(start_response)

    return application


def _build_router() -> Router:
    router = Router()
    router.add("GET", "/health", _health_check, public=True)
    router.add("GET", "/me", _get_me, permissions=("profile:read",))
    router.add("GET", "/users", _list_users, permissions=("users:manage",))
    router.add("POST", "/users", _create_user, permissions=("users:manage",))
    router.add("GET", "/users/{user_id}", _get_user, permissions=("users:manage",))
    router.add("PATCH", "/users/{user_id}", _update_user, permissions=("users:manage",))
    router.add("GET", "/records", _list_records, permissions=("records:read",))
    router.add("POST", "/records", _create_record, permissions=("records:write",))
    router.add("GET", "/records/{record_id}", _get_record, permissions=("records:read",))
    router.add(
        "PATCH",
        "/records/{record_id}",
        _update_record,
        permissions=("records:write",),
    )
    router.add(
        "DELETE",
        "/records/{record_id}",
        _delete_record,
        permissions=("records:write",),
    )
    router.add(
        "GET",
        "/dashboard/summary",
        _get_dashboard_summary,
        permissions=("dashboard:read",),
    )
    return router


def _health_check(request: Request, connection: sqlite3.Connection) -> Response:
    connection.execute("SELECT 1")
    return Response(
        payload={
            "status": "ok",
            "service": "finance-dashboard-backend",
        }
    )


def _get_me(request: Request, connection: sqlite3.Connection) -> Response:
    return Response(payload={"data": request.current_user})


def _list_users(request: Request, connection: sqlite3.Connection) -> Response:
    service = UserService(connection)
    return Response(payload={"data": service.list_users()})


def _create_user(request: Request, connection: sqlite3.Connection) -> Response:
    payload = validate_user_payload(request.json())
    service = UserService(connection)
    user = service.create_user(payload)
    return Response(status_code=201, payload={"data": user})


def _get_user(request: Request, connection: sqlite3.Connection) -> Response:
    service = UserService(connection)
    user_id = _path_param_as_int(request, "user_id")
    return Response(payload={"data": service.get_user(user_id)})


def _update_user(request: Request, connection: sqlite3.Connection) -> Response:
    payload = validate_user_payload(request.json(), partial=True)
    service = UserService(connection)
    user_id = _path_param_as_int(request, "user_id")
    user = service.update_user(user_id, payload)
    return Response(payload={"data": user})


def _list_records(request: Request, connection: sqlite3.Connection) -> Response:
    filters = validate_record_filters(request.query)
    service = RecordService(connection)
    return Response(payload=service.list_records(filters))


def _create_record(request: Request, connection: sqlite3.Connection) -> Response:
    payload = validate_record_payload(request.json())
    service = RecordService(connection)
    record = service.create_record(payload, request.current_user or {})
    return Response(status_code=201, payload={"data": record})


def _get_record(request: Request, connection: sqlite3.Connection) -> Response:
    service = RecordService(connection)
    record_id = _path_param_as_int(request, "record_id")
    return Response(payload={"data": service.get_record(record_id)})


def _update_record(request: Request, connection: sqlite3.Connection) -> Response:
    payload = validate_record_payload(request.json(), partial=True)
    service = RecordService(connection)
    record_id = _path_param_as_int(request, "record_id")
    record = service.update_record(record_id, payload, request.current_user or {})
    return Response(payload={"data": record})


def _delete_record(request: Request, connection: sqlite3.Connection) -> Response:
    service = RecordService(connection)
    record_id = _path_param_as_int(request, "record_id")
    service.delete_record(record_id)
    return Response(status_code=204)


def _get_dashboard_summary(
    request: Request, connection: sqlite3.Connection
) -> Response:
    filters = validate_summary_filters(request.query)
    service = DashboardService(connection)
    return Response(payload={"data": service.get_summary(filters)})


def _path_param_as_int(request: Request, key: str) -> int:
    value = request.path_params.get(key)
    if value is None:
        raise ValidationError(f"Missing path parameter: {key}")
    return require_int(value, key)
