from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from finance_backend.errors import ValidationError


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_ROLES = {"viewer", "analyst", "admin"}
VALID_STATUSES = {"active", "inactive"}
VALID_RECORD_TYPES = {"income", "expense"}


def require_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an integer.") from exc


def parse_iso_date(value: str, field_name: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must use ISO format YYYY-MM-DD."
        ) from exc
    return parsed.isoformat()


def parse_amount_to_cents(value: Any, field_name: str = "amount") -> int:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc
    if decimal_value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    cents = (decimal_value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_amount(value: int) -> float:
    return float((Decimal(value) / Decimal("100")).quantize(Decimal("0.01")))


def validate_user_payload(
    payload: dict[str, Any], *, partial: bool = False
) -> dict[str, Any]:
    allowed_fields = {"name", "email", "role", "status"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise ValidationError(
            "Request contains unsupported user fields.",
            details={"fields": unknown_fields},
        )
    if not partial and not payload:
        raise ValidationError("User payload is required.")

    validated: dict[str, Any] = {}
    if "name" in payload:
        name = str(payload["name"]).strip()
        if len(name) < 2:
            raise ValidationError("name must contain at least 2 characters.")
        validated["name"] = name
    elif not partial:
        raise ValidationError("name is required.")

    if "email" in payload:
        email = str(payload["email"]).strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise ValidationError("email must be a valid email address.")
        validated["email"] = email
    elif not partial:
        raise ValidationError("email is required.")

    if "role" in payload:
        role = str(payload["role"]).strip().lower()
        if role not in VALID_ROLES:
            raise ValidationError(
                "role must be one of viewer, analyst, or admin."
            )
        validated["role"] = role
    elif not partial:
        raise ValidationError("role is required.")

    if "status" in payload:
        status = str(payload["status"]).strip().lower()
        if status not in VALID_STATUSES:
            raise ValidationError("status must be active or inactive.")
        validated["status"] = status
    elif not partial:
        validated["status"] = "active"

    if partial and not validated:
        raise ValidationError("At least one user field must be provided.")
    return validated


def validate_record_payload(
    payload: dict[str, Any], *, partial: bool = False
) -> dict[str, Any]:
    allowed_fields = {"amount", "type", "category", "date", "notes"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise ValidationError(
            "Request contains unsupported record fields.",
            details={"fields": unknown_fields},
        )
    if not partial and not payload:
        raise ValidationError("Record payload is required.")

    validated: dict[str, Any] = {}
    if "amount" in payload:
        validated["amount_cents"] = parse_amount_to_cents(payload["amount"])
    elif not partial:
        raise ValidationError("amount is required.")

    if "type" in payload:
        record_type = str(payload["type"]).strip().lower()
        if record_type not in VALID_RECORD_TYPES:
            raise ValidationError("type must be income or expense.")
        validated["type"] = record_type
    elif not partial:
        raise ValidationError("type is required.")

    if "category" in payload:
        category = str(payload["category"]).strip()
        if len(category) < 2:
            raise ValidationError("category must contain at least 2 characters.")
        validated["category"] = category
    elif not partial:
        raise ValidationError("category is required.")

    if "date" in payload:
        validated["record_date"] = parse_iso_date(str(payload["date"]), "date")
    elif not partial:
        raise ValidationError("date is required.")

    if "notes" in payload:
        notes = str(payload["notes"]).strip()
        if len(notes) > 500:
            raise ValidationError("notes cannot exceed 500 characters.")
        validated["notes"] = notes
    elif not partial:
        validated["notes"] = ""

    if partial and not validated:
        raise ValidationError("At least one record field must be provided.")
    return validated


def validate_record_filters(query: dict[str, list[str]]) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "limit": 20,
        "offset": 0,
    }

    if query.get("type"):
        record_type = query["type"][-1].strip().lower()
        if record_type not in VALID_RECORD_TYPES:
            raise ValidationError("type filter must be income or expense.")
        filters["type"] = record_type

    if query.get("category"):
        category = query["category"][-1].strip()
        if not category:
            raise ValidationError("category filter cannot be empty.")
        filters["category"] = category

    if query.get("date_from"):
        filters["date_from"] = parse_iso_date(query["date_from"][-1], "date_from")

    if query.get("date_to"):
        filters["date_to"] = parse_iso_date(query["date_to"][-1], "date_to")

    if query.get("min_amount"):
        filters["min_amount_cents"] = parse_amount_to_cents(
            query["min_amount"][-1], "min_amount"
        )

    if query.get("max_amount"):
        filters["max_amount_cents"] = parse_amount_to_cents(
            query["max_amount"][-1], "max_amount"
        )

    if query.get("search"):
        search = query["search"][-1].strip()
        if search:
            filters["search"] = search

    if query.get("limit"):
        filters["limit"] = require_int(query["limit"][-1], "limit")
    if query.get("offset"):
        filters["offset"] = require_int(query["offset"][-1], "offset")

    if filters["limit"] < 1 or filters["limit"] > 100:
        raise ValidationError("limit must be between 1 and 100.")
    if filters["offset"] < 0:
        raise ValidationError("offset cannot be negative.")
    if (
        "min_amount_cents" in filters
        and "max_amount_cents" in filters
        and filters["min_amount_cents"] > filters["max_amount_cents"]
    ):
        raise ValidationError("min_amount cannot be greater than max_amount.")
    if (
        "date_from" in filters
        and "date_to" in filters
        and filters["date_from"] > filters["date_to"]
    ):
        raise ValidationError("date_from cannot be later than date_to.")
    return filters


def validate_summary_filters(query: dict[str, list[str]]) -> dict[str, Any]:
    filters = validate_record_filters(query)
    filters["recent_limit"] = 5
    filters["trend_months"] = 6
    filters.pop("limit", None)
    filters.pop("offset", None)
    filters.pop("search", None)
    if query.get("recent_limit"):
        filters["recent_limit"] = require_int(query["recent_limit"][-1], "recent_limit")
    if query.get("trend_months"):
        filters["trend_months"] = require_int(query["trend_months"][-1], "trend_months")
    if filters["recent_limit"] < 1 or filters["recent_limit"] > 20:
        raise ValidationError("recent_limit must be between 1 and 20.")
    if filters["trend_months"] < 1 or filters["trend_months"] > 24:
        raise ValidationError("trend_months must be between 1 and 24.")
    return filters
