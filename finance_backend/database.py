from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def get_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path, *, seed_demo_records: bool) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = get_connection(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                role TEXT NOT NULL CHECK (role IN ('viewer', 'analyst', 'admin')),
                status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS financial_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                category TEXT NOT NULL,
                record_date TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_by INTEGER NOT NULL REFERENCES users(id),
                updated_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_financial_records_date
                ON financial_records(record_date);
            CREATE INDEX IF NOT EXISTS idx_financial_records_type
                ON financial_records(type);
            CREATE INDEX IF NOT EXISTS idx_financial_records_category
                ON financial_records(category);
            """
        )
        _seed_users(connection)
        if seed_demo_records:
            _seed_records(connection)
        connection.commit()
    finally:
        connection.close()


def _seed_users(connection: sqlite3.Connection) -> None:
    now = utc_now()
    users = [
        (1, "Ava Admin", "admin@finance.local", "admin", "active", now, now),
        (2, "Noah Analyst", "analyst@finance.local", "analyst", "active", now, now),
        (3, "Vera Viewer", "viewer@finance.local", "viewer", "active", now, now),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO users (id, name, email, role, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        users,
    )


def _seed_records(connection: sqlite3.Connection) -> None:
    existing_count = connection.execute(
        "SELECT COUNT(*) AS total FROM financial_records"
    ).fetchone()["total"]
    if existing_count > 0:
        return
    now = utc_now()
    records = [
        (320000, "income", "Consulting", "2026-03-10", "March consulting retainer", 1, 1, now, now),
        (85000, "expense", "Payroll", "2026-03-12", "Operations contractor payout", 1, 1, now, now),
        (18000, "expense", "Software", "2026-03-18", "Annual tooling subscription", 1, 1, now, now),
        (95000, "income", "Investments", "2026-04-01", "Dividend income", 1, 1, now, now),
        (12000, "expense", "Travel", "2026-04-02", "Client visit transport", 1, 1, now, now),
    ]
    connection.executemany(
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
        records,
    )
