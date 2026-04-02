from __future__ import annotations

import sqlite3
from typing import Any

from finance_backend.database import utc_now
from finance_backend.errors import ConflictError, NotFoundError
from finance_backend.validation import cents_to_amount


def user_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "amount": cents_to_amount(row["amount_cents"]),
        "type": row["type"],
        "category": row["category"],
        "date": row["record_date"],
        "notes": row["notes"],
        "created_by": row["created_by"],
        "updated_by": row["updated_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class UserService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_users(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT id, name, email, role, status, created_at, updated_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()
        return [user_to_dict(row) for row in rows]

    def get_user(self, user_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT id, name, email, role, status, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("User not found.")
        return user_to_dict(row)

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        try:
            cursor = self.connection.execute(
                """
                INSERT INTO users (name, email, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["name"],
                    payload["email"],
                    payload["role"],
                    payload["status"],
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("A user with this email already exists.") from exc
        return self.get_user(cursor.lastrowid)

    def update_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.get_user(user_id)
        columns = []
        values = []
        for key in ("name", "email", "role", "status"):
            if key in payload:
                columns.append(f"{key} = ?")
                values.append(payload[key])
        values.extend([utc_now(), user_id])
        try:
            self.connection.execute(
                f"""
                UPDATE users
                SET {", ".join(columns)}, updated_at = ?
                WHERE id = ?
                """,
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("A user with this email already exists.") from exc
        return self.get_user(user_id)


class RecordService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_records(self, filters: dict[str, Any]) -> dict[str, Any]:
        where_sql, parameters = _build_record_filters(filters)
        total = self.connection.execute(
            f"SELECT COUNT(*) AS total FROM financial_records {where_sql}",
            parameters,
        ).fetchone()["total"]
        rows = self.connection.execute(
            f"""
            SELECT
                id,
                amount_cents,
                type,
                category,
                record_date,
                notes,
                created_by,
                updated_by,
                created_at,
                updated_at
            FROM financial_records
            {where_sql}
            ORDER BY record_date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*parameters, filters["limit"], filters["offset"]],
        ).fetchall()
        return {
            "data": [record_to_dict(row) for row in rows],
            "pagination": {
                "limit": filters["limit"],
                "offset": filters["offset"],
                "total": total,
            },
        }

    def get_record(self, record_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT
                id,
                amount_cents,
                type,
                category,
                record_date,
                notes,
                created_by,
                updated_by,
                created_at,
                updated_at
            FROM financial_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("Financial record not found.")
        return record_to_dict(row)

    def create_record(
        self, payload: dict[str, Any], current_user: dict[str, Any]
    ) -> dict[str, Any]:
        now = utc_now()
        cursor = self.connection.execute(
            """
            INSERT INTO financial_records (
                amount_cents,
                type,
                category,
                record_date,
                notes,
                created_by,
                updated_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["amount_cents"],
                payload["type"],
                payload["category"],
                payload["record_date"],
                payload["notes"],
                current_user["id"],
                current_user["id"],
                now,
                now,
            ),
        )
        return self.get_record(cursor.lastrowid)

    def update_record(
        self, record_id: int, payload: dict[str, Any], current_user: dict[str, Any]
    ) -> dict[str, Any]:
        self.get_record(record_id)
        columns = []
        values = []
        mapping = {
            "amount_cents": "amount_cents",
            "type": "type",
            "category": "category",
            "record_date": "record_date",
            "notes": "notes",
        }
        for payload_key, column_name in mapping.items():
            if payload_key in payload:
                columns.append(f"{column_name} = ?")
                values.append(payload[payload_key])
        values.extend([current_user["id"], utc_now(), record_id])
        self.connection.execute(
            f"""
            UPDATE financial_records
            SET {", ".join(columns)}, updated_by = ?, updated_at = ?
            WHERE id = ?
            """,
            values,
        )
        return self.get_record(record_id)

    def delete_record(self, record_id: int) -> None:
        self.get_record(record_id)
        self.connection.execute(
            "DELETE FROM financial_records WHERE id = ?",
            (record_id,),
        )


class DashboardService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_summary(self, filters: dict[str, Any]) -> dict[str, Any]:
        where_sql, parameters = _build_record_filters(filters)
        totals = {"income": 0, "expense": 0}
        total_rows = self.connection.execute(
            f"""
            SELECT type, COALESCE(SUM(amount_cents), 0) AS total_cents
            FROM financial_records
            {where_sql}
            GROUP BY type
            """,
            parameters,
        ).fetchall()
        for row in total_rows:
            totals[row["type"]] = row["total_cents"] or 0

        category_rows = self.connection.execute(
            f"""
            SELECT category, type, COALESCE(SUM(amount_cents), 0) AS total_cents
            FROM financial_records
            {where_sql}
            GROUP BY category, type
            ORDER BY total_cents DESC, category ASC
            """,
            parameters,
        ).fetchall()

        recent_rows = self.connection.execute(
            f"""
            SELECT
                id,
                amount_cents,
                type,
                category,
                record_date,
                notes,
                created_by,
                updated_by,
                created_at,
                updated_at
            FROM financial_records
            {where_sql}
            ORDER BY record_date DESC, id DESC
            LIMIT ?
            """,
            [*parameters, filters["recent_limit"]],
        ).fetchall()

        trend_rows = self.connection.execute(
            f"""
            SELECT
                strftime('%Y-%m', record_date) AS period,
                type,
                COALESCE(SUM(amount_cents), 0) AS total_cents
            FROM financial_records
            {where_sql}
            GROUP BY period, type
            ORDER BY period DESC
            """,
            parameters,
        ).fetchall()

        return {
            "totals": {
                "income": cents_to_amount(totals["income"]),
                "expenses": cents_to_amount(totals["expense"]),
                "net_balance": cents_to_amount(totals["income"] - totals["expense"]),
            },
            "category_totals": [
                {
                    "category": row["category"],
                    "type": row["type"],
                    "total": cents_to_amount(row["total_cents"]),
                }
                for row in category_rows
            ],
            "recent_activity": [record_to_dict(row) for row in recent_rows],
            "monthly_trends": _build_monthly_trends(
                trend_rows, filters["trend_months"]
            ),
            "filters": {
                key: value
                for key, value in filters.items()
                if key
                in {
                    "type",
                    "category",
                    "date_from",
                    "date_to",
                    "min_amount_cents",
                    "max_amount_cents",
                }
            },
        }


def _build_record_filters(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses = []
    parameters: list[Any] = []
    if filters.get("type"):
        clauses.append("type = ?")
        parameters.append(filters["type"])
    if filters.get("category"):
        clauses.append("category = ?")
        parameters.append(filters["category"])
    if filters.get("date_from"):
        clauses.append("record_date >= ?")
        parameters.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("record_date <= ?")
        parameters.append(filters["date_to"])
    if filters.get("min_amount_cents") is not None:
        clauses.append("amount_cents >= ?")
        parameters.append(filters["min_amount_cents"])
    if filters.get("max_amount_cents") is not None:
        clauses.append("amount_cents <= ?")
        parameters.append(filters["max_amount_cents"])
    if filters.get("search"):
        clauses.append("(category LIKE ? OR notes LIKE ?)")
        pattern = f"%{filters['search']}%"
        parameters.extend([pattern, pattern])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, parameters


def _build_monthly_trends(
    rows: list[sqlite3.Row], trend_months: int
) -> list[dict[str, Any]]:
    periods: list[str] = []
    totals_by_period: dict[str, dict[str, int]] = {}
    for row in rows:
        period = row["period"]
        if period not in totals_by_period:
            if len(periods) >= trend_months:
                continue
            periods.append(period)
            totals_by_period[period] = {"income": 0, "expense": 0}
        totals_by_period[period][row["type"]] = row["total_cents"]

    serialized = []
    for period in sorted(periods):
        income = totals_by_period[period]["income"]
        expense = totals_by_period[period]["expense"]
        serialized.append(
            {
                "period": period,
                "income": cents_to_amount(income),
                "expenses": cents_to_amount(expense),
                "net_balance": cents_to_amount(income - expense),
            }
        )
    return serialized
