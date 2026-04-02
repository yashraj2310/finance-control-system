from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from finance_backend.app import create_app
from finance_backend.config import AppConfig


class WSGITestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def request(
        self,
        method: str,
        path: str,
        *,
        user_id: int | None = None,
        json_body: dict[str, Any] | None = None,
        raw_body: bytes | None = None,
        content_type: str | None = None,
        query: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], Any]:
        if query:
            separator = "&" if "?" in path else "?"
            path = f"{path}{separator}{urlencode(query)}"
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        else:
            path_info, query_string = path, ""

        body = b""
        environ = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SCRIPT_NAME": "",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(body),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": "0",
        }

        if user_id is not None:
            environ["HTTP_X_USER_ID"] = str(user_id)

        if json_body is not None and raw_body is not None:
            raise ValueError("Pass either json_body or raw_body, not both.")

        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            environ["wsgi.input"] = io.BytesIO(body)
            environ["CONTENT_LENGTH"] = str(len(body))
            environ["CONTENT_TYPE"] = "application/json"
        elif raw_body is not None:
            body = raw_body
            environ["wsgi.input"] = io.BytesIO(body)
            environ["CONTENT_LENGTH"] = str(len(body))
            if content_type is not None:
                environ["CONTENT_TYPE"] = content_type

        status_holder: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            status_holder["status"] = status
            status_holder["headers"] = dict(headers)

        body_bytes = b"".join(self.app(environ, start_response))
        payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        status_code = int(status_holder["status"].split(" ", 1)[0])
        return status_code, status_holder["headers"], payload


class FinanceBackendAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config = AppConfig(
            database_path=Path(self.temp_dir.name) / "finance.db",
            seed_demo_records=False,
        )
        self.client = WSGITestClient(create_app(config))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_check_is_public(self) -> None:
        status, _, payload = self.client.request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_viewer_can_read_summary_but_not_records(self) -> None:
        self._create_record(
            {
                "amount": 1200,
                "type": "income",
                "category": "Sales",
                "date": "2026-01-15",
                "notes": "January invoice",
            }
        )

        status, _, summary = self.client.request("GET", "/dashboard/summary", user_id=3)
        denied_status, _, denied_payload = self.client.request("GET", "/records", user_id=3)

        self.assertEqual(status, 200)
        self.assertEqual(summary["data"]["totals"]["income"], 1200.0)
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied_payload["error"]["code"], "forbidden")

    def test_analyst_can_read_records_but_cannot_create_them(self) -> None:
        self._create_record(
            {
                "amount": 450,
                "type": "expense",
                "category": "Tools",
                "date": "2026-02-03",
                "notes": "Team license",
            }
        )

        status, _, payload = self.client.request("GET", "/records", user_id=2)
        denied_status, _, denied_payload = self.client.request(
            "POST",
            "/records",
            user_id=2,
            json_body={
                "amount": 50,
                "type": "expense",
                "category": "Travel",
                "date": "2026-02-04",
                "notes": "Taxi",
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["pagination"]["total"], 1)
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied_payload["error"]["code"], "forbidden")

    def test_admin_can_manage_users_and_inactive_users_are_blocked(self) -> None:
        status, _, created_payload = self.client.request(
            "POST",
            "/users",
            user_id=1,
            json_body={
                "name": "Iris Insight",
                "email": "iris@example.com",
                "role": "analyst",
                "status": "active",
            },
        )
        user_id = created_payload["data"]["id"]

        update_status, _, updated_payload = self.client.request(
            "PATCH",
            f"/users/{user_id}",
            user_id=1,
            json_body={"status": "inactive"},
        )
        denied_status, _, denied_payload = self.client.request(
            "GET",
            "/dashboard/summary",
            user_id=user_id,
        )

        self.assertEqual(status, 201)
        self.assertEqual(update_status, 200)
        self.assertEqual(updated_payload["data"]["status"], "inactive")
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied_payload["error"]["message"], "Inactive users cannot access the API.")

    def test_record_filters_and_summary_totals_are_correct(self) -> None:
        self._create_record(
            {
                "amount": 1000,
                "type": "income",
                "category": "Consulting",
                "date": "2026-01-10",
                "notes": "Advisory work",
            }
        )
        self._create_record(
            {
                "amount": 200,
                "type": "expense",
                "category": "Software",
                "date": "2026-01-11",
                "notes": "Monthly license",
            }
        )
        self._create_record(
            {
                "amount": 500,
                "type": "income",
                "category": "Investments",
                "date": "2026-02-01",
                "notes": "Bond payout",
            }
        )

        status, _, records_payload = self.client.request(
            "GET",
            "/records",
            user_id=2,
            query={"type": "expense"},
        )
        summary_status, _, summary_payload = self.client.request(
            "GET",
            "/dashboard/summary",
            user_id=2,
            query={
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "trend_months": 12,
                "recent_limit": 2,
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(records_payload["pagination"]["total"], 1)
        self.assertEqual(records_payload["data"][0]["category"], "Software")
        self.assertEqual(summary_status, 200)
        self.assertEqual(summary_payload["data"]["totals"]["income"], 1000.0)
        self.assertEqual(summary_payload["data"]["totals"]["expenses"], 200.0)
        self.assertEqual(summary_payload["data"]["totals"]["net_balance"], 800.0)
        self.assertEqual(summary_payload["data"]["monthly_trends"][0]["period"], "2026-01")
        self.assertEqual(len(summary_payload["data"]["recent_activity"]), 2)

    def test_invalid_record_payload_returns_validation_error(self) -> None:
        status, _, payload = self.client.request(
            "POST",
            "/records",
            user_id=1,
            json_body={
                "amount": -20,
                "type": "expense",
                "category": "Ops",
                "date": "2026-99-01",
            },
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "validation_error")

    def test_invalid_json_body_returns_validation_error(self) -> None:
        status, _, payload = self.client.request(
            "POST",
            "/records",
            user_id=1,
            raw_body=b"{bad json}",
            content_type="application/json",
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "validation_error")
        self.assertEqual(
            payload["error"]["message"], "Request body must contain valid JSON."
        )

    def test_invalid_utf8_body_returns_validation_error(self) -> None:
        status, _, payload = self.client.request(
            "POST",
            "/records",
            user_id=1,
            raw_body=b"\xff\xfe\xfd",
            content_type="application/json",
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "validation_error")
        self.assertEqual(
            payload["error"]["message"], "Request body must be UTF-8 encoded JSON."
        )

    def test_wrong_http_method_returns_405_and_allow_header(self) -> None:
        status, headers, payload = self.client.request("POST", "/health")

        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET")
        self.assertEqual(payload["error"]["code"], "method_not_allowed")

    def test_delete_record_returns_204_and_record_is_removed(self) -> None:
        record = self._create_record(
            {
                "amount": 75,
                "type": "expense",
                "category": "Travel",
                "date": "2026-03-06",
                "notes": "Cab fare",
            }
        )

        delete_status, _, delete_payload = self.client.request(
            "DELETE",
            f"/records/{record['id']}",
            user_id=1,
        )
        get_status, _, get_payload = self.client.request(
            "GET",
            f"/records/{record['id']}",
            user_id=2,
        )

        self.assertEqual(delete_status, 204)
        self.assertIsNone(delete_payload)
        self.assertEqual(get_status, 404)
        self.assertEqual(get_payload["error"]["code"], "not_found")

    def _create_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        status, _, response_payload = self.client.request(
            "POST",
            "/records",
            user_id=1,
            json_body=payload,
        )
        self.assertEqual(status, 201)
        return response_payload["data"]


if __name__ == "__main__":
    unittest.main()
