# Finance Dashboard Backend API Documentation

## 1. Overview

This document describes the backend APIs for the Finance Data Processing and Access Control project.

The API supports:

- User and role management
- Financial record management
- Dashboard summary and analytics
- Role-based access control
- Validation and structured error responses

## 2. Base URL

Use one of the following depending on where the backend is running:

- Local: `http://127.0.0.1:8000`
- Live: `https://your-live-url`

## 3. Authentication

This project uses mock authentication through a request header:

`X-User-Id: <user_id>`

The backend reads this header, loads the corresponding user from the database, and applies role-based authorization.

### Seeded Users

| User ID | Name | Role |
| --- | --- | --- |
| `1` | Ava Admin | `admin` |
| `2` | Noah Analyst | `analyst` |
| `3` | Vera Viewer | `viewer` |

If a user is marked as `inactive`, access is denied even if the role normally allows the action.

## 4. Roles and Permissions

| Role | Allowed Actions |
| --- | --- |
| `viewer` | Read profile, read dashboard summary |
| `analyst` | Read profile, read dashboard summary, read records |
| `admin` | Full access to users, records, and dashboard summary |

## 5. Common Conventions

### Content Type

For requests with a body:

`Content-Type: application/json`

### Date Format

All dates use ISO format:

`YYYY-MM-DD`

Example:

`2026-04-02`

### Amount Format

- Request bodies use `amount` as a number
- Responses return `amount` as a decimal number
- Internally the system stores amounts in integer cents

Example:

```json
{
  "amount": 1250.75
}
```

### Standard Error Format

```json
{
  "error": {
    "code": "validation_error",
    "message": "date must use ISO format YYYY-MM-DD."
  }
}
```

## 6. Status Codes

| Status Code | Meaning |
| --- | --- |
| `200` | Success |
| `201` | Resource created |
| `204` | Resource deleted successfully |
| `400` | Validation or bad request |
| `401` | Authentication missing or invalid |
| `403` | Forbidden for current role or inactive user |
| `404` | Resource not found |
| `409` | Conflict, such as duplicate email |
| `500` | Internal server error |

---

## 7. API Endpoints

### 7.1 Health Check

#### `GET /health`

Checks whether the service is running.

### Access

Public

### Example Request

```bash
curl http://127.0.0.1:8000/health
```

### Example Response

```json
{
  "status": "ok",
  "service": "finance-dashboard-backend"
}
```

---

### 7.2 Current User Profile

#### `GET /me`

Returns the currently authenticated user.

### Access

`viewer`, `analyst`, `admin`

### Headers

`X-User-Id: 1`

### Example Request

```bash
curl -H "X-User-Id: 1" http://127.0.0.1:8000/me
```

### Example Response

```json
{
  "data": {
    "id": 1,
    "name": "Ava Admin",
    "email": "admin@finance.local",
    "role": "admin",
    "status": "active",
    "created_at": "2026-04-02T10:00:00+00:00",
    "updated_at": "2026-04-02T10:00:00+00:00"
  }
}
```

---

## 8. User Management APIs

All user management endpoints are restricted to `admin`.

### 8.1 List Users

#### `GET /users`

Returns all users.

### Access

`admin`

### Example Request

```bash
curl -H "X-User-Id: 1" http://127.0.0.1:8000/users
```

### Example Response

```json
{
  "data": [
    {
      "id": 1,
      "name": "Ava Admin",
      "email": "admin@finance.local",
      "role": "admin",
      "status": "active",
      "created_at": "2026-04-02T10:00:00+00:00",
      "updated_at": "2026-04-02T10:00:00+00:00"
    }
  ]
}
```

### 8.2 Create User

#### `POST /users`

Creates a new user.

### Access

`admin`

### Request Body

```json
{
  "name": "Iris Insight",
  "email": "iris@example.com",
  "role": "analyst",
  "status": "active"
}
```

### Field Rules

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | string | Yes | Minimum 2 characters |
| `email` | string | Yes | Must be a valid email |
| `role` | string | Yes | `viewer`, `analyst`, or `admin` |
| `status` | string | No | Defaults to `active` if omitted |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/users ^
  -H "Content-Type: application/json" ^
  -H "X-User-Id: 1" ^
  -d "{\"name\":\"Iris Insight\",\"email\":\"iris@example.com\",\"role\":\"analyst\",\"status\":\"active\"}"
```

### Example Response

```json
{
  "data": {
    "id": 4,
    "name": "Iris Insight",
    "email": "iris@example.com",
    "role": "analyst",
    "status": "active",
    "created_at": "2026-04-02T10:10:00+00:00",
    "updated_at": "2026-04-02T10:10:00+00:00"
  }
}
```

### 8.3 Get User By ID

#### `GET /users/{user_id}`

Returns a single user.

### Access

`admin`

### Path Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `user_id` | integer | User identifier |

### Example Request

```bash
curl -H "X-User-Id: 1" http://127.0.0.1:8000/users/2
```

### 8.4 Update User

#### `PATCH /users/{user_id}`

Partially updates a user.

### Access

`admin`

### Request Body

Any subset of the fields below:

```json
{
  "status": "inactive"
}
```

### Updatable Fields

- `name`
- `email`
- `role`
- `status`

### Example Request

```bash
curl -X PATCH http://127.0.0.1:8000/users/4 ^
  -H "Content-Type: application/json" ^
  -H "X-User-Id: 1" ^
  -d "{\"status\":\"inactive\"}"
```

### Example Response

```json
{
  "data": {
    "id": 4,
    "name": "Iris Insight",
    "email": "iris@example.com",
    "role": "analyst",
    "status": "inactive",
    "created_at": "2026-04-02T10:10:00+00:00",
    "updated_at": "2026-04-02T10:15:00+00:00"
  }
}
```

---

## 9. Financial Records APIs

### Record Object

```json
{
  "id": 10,
  "amount": 1250.75,
  "type": "income",
  "category": "Consulting",
  "date": "2026-04-02",
  "notes": "Quarterly retainer",
  "created_by": 1,
  "updated_by": 1,
  "created_at": "2026-04-02T10:20:00+00:00",
  "updated_at": "2026-04-02T10:20:00+00:00"
}
```

### 9.1 List Records

#### `GET /records`

Returns paginated financial records.

### Access

`analyst`, `admin`

### Query Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | string | No | `income` or `expense` |
| `category` | string | No | Exact category match |
| `date_from` | string | No | Start date filter |
| `date_to` | string | No | End date filter |
| `min_amount` | number | No | Minimum amount |
| `max_amount` | number | No | Maximum amount |
| `search` | string | No | Searches category and notes |
| `limit` | integer | No | Default `20`, max `100` |
| `offset` | integer | No | Default `0` |

### Example Request

```bash
curl -H "X-User-Id: 2" "http://127.0.0.1:8000/records?type=expense&limit=10&offset=0"
```

### Example Response

```json
{
  "data": [
    {
      "id": 5,
      "amount": 200.0,
      "type": "expense",
      "category": "Software",
      "date": "2026-01-11",
      "notes": "Monthly license",
      "created_by": 1,
      "updated_by": 1,
      "created_at": "2026-04-02T10:20:00+00:00",
      "updated_at": "2026-04-02T10:20:00+00:00"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 1
  }
}
```

### 9.2 Create Record

#### `POST /records`

Creates a financial record.

### Access

`admin`

### Request Body

```json
{
  "amount": 1250.75,
  "type": "income",
  "category": "Consulting",
  "date": "2026-04-02",
  "notes": "Quarterly retainer"
}
```

### Field Rules

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `amount` | number | Yes | Must be greater than zero |
| `type` | string | Yes | `income` or `expense` |
| `category` | string | Yes | Minimum 2 characters |
| `date` | string | Yes | ISO date `YYYY-MM-DD` |
| `notes` | string | No | Maximum 500 characters |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/records ^
  -H "Content-Type: application/json" ^
  -H "X-User-Id: 1" ^
  -d "{\"amount\":1250.75,\"type\":\"income\",\"category\":\"Consulting\",\"date\":\"2026-04-02\",\"notes\":\"Quarterly retainer\"}"
```

### Example Response

```json
{
  "data": {
    "id": 10,
    "amount": 1250.75,
    "type": "income",
    "category": "Consulting",
    "date": "2026-04-02",
    "notes": "Quarterly retainer",
    "created_by": 1,
    "updated_by": 1,
    "created_at": "2026-04-02T10:20:00+00:00",
    "updated_at": "2026-04-02T10:20:00+00:00"
  }
}
```

### 9.3 Get Record By ID

#### `GET /records/{record_id}`

Returns a single financial record.

### Access

`analyst`, `admin`

### Path Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `record_id` | integer | Record identifier |

### Example Request

```bash
curl -H "X-User-Id: 2" http://127.0.0.1:8000/records/10
```

### 9.4 Update Record

#### `PATCH /records/{record_id}`

Partially updates a financial record.

### Access

`admin`

### Request Body

Any subset of the fields below:

```json
{
  "notes": "Updated note",
  "category": "Advisory"
}
```

### Updatable Fields

- `amount`
- `type`
- `category`
- `date`
- `notes`

### Example Request

```bash
curl -X PATCH http://127.0.0.1:8000/records/10 ^
  -H "Content-Type: application/json" ^
  -H "X-User-Id: 1" ^
  -d "{\"notes\":\"Updated quarterly retainer note\"}"
```

### Example Response

```json
{
  "data": {
    "id": 10,
    "amount": 1250.75,
    "type": "income",
    "category": "Consulting",
    "date": "2026-04-02",
    "notes": "Updated quarterly retainer note",
    "created_by": 1,
    "updated_by": 1,
    "created_at": "2026-04-02T10:20:00+00:00",
    "updated_at": "2026-04-02T10:30:00+00:00"
  }
}
```

### 9.5 Delete Record

#### `DELETE /records/{record_id}`

Deletes a financial record permanently.

### Access

`admin`

### Example Request

```bash
curl -X DELETE -H "X-User-Id: 1" http://127.0.0.1:8000/records/10
```

### Example Response

No response body.

Status:

`204 No Content`

---

## 10. Dashboard Summary API

### 10.1 Get Dashboard Summary

#### `GET /dashboard/summary`

Returns aggregated finance data for dashboard use.

### Access

`viewer`, `analyst`, `admin`

### Query Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | string | No | `income` or `expense` |
| `category` | string | No | Exact category match |
| `date_from` | string | No | Start date filter |
| `date_to` | string | No | End date filter |
| `min_amount` | number | No | Minimum amount |
| `max_amount` | number | No | Maximum amount |
| `recent_limit` | integer | No | Default `5`, max `20` |
| `trend_months` | integer | No | Default `6`, max `24` |

### Example Request

```bash
curl -H "X-User-Id: 3" "http://127.0.0.1:8000/dashboard/summary?date_from=2026-01-01&date_to=2026-12-31&recent_limit=5&trend_months=6"
```

### Example Response

```json
{
  "data": {
    "totals": {
      "income": 1500.0,
      "expenses": 200.0,
      "net_balance": 1300.0
    },
    "category_totals": [
      {
        "category": "Consulting",
        "type": "income",
        "total": 1000.0
      },
      {
        "category": "Software",
        "type": "expense",
        "total": 200.0
      },
      {
        "category": "Investments",
        "type": "income",
        "total": 500.0
      }
    ],
    "recent_activity": [
      {
        "id": 3,
        "amount": 500.0,
        "type": "income",
        "category": "Investments",
        "date": "2026-02-01",
        "notes": "Bond payout",
        "created_by": 1,
        "updated_by": 1,
        "created_at": "2026-04-02T10:20:00+00:00",
        "updated_at": "2026-04-02T10:20:00+00:00"
      }
    ],
    "monthly_trends": [
      {
        "period": "2026-01",
        "income": 1000.0,
        "expenses": 200.0,
        "net_balance": 800.0
      },
      {
        "period": "2026-02",
        "income": 500.0,
        "expenses": 0.0,
        "net_balance": 500.0
      }
    ],
    "filters": {
      "date_from": "2026-01-01",
      "date_to": "2026-12-31"
    }
  }
}
```

### Response Sections

| Section | Description |
| --- | --- |
| `totals` | Total income, total expenses, and net balance |
| `category_totals` | Aggregated totals grouped by category and type |
| `recent_activity` | Most recent matching records |
| `monthly_trends` | Month-by-month income, expenses, and net balance |
| `filters` | Applied filter values |

---

## 11. Error Examples

### 11.1 Missing Authentication Header

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication is required. Provide the X-User-Id header."
  }
}
```

### 11.2 Forbidden By Role

```json
{
  "error": {
    "code": "forbidden",
    "message": "This action is not allowed for your role.",
    "details": {
      "required_permissions": [
        "records:write"
      ],
      "role": "analyst"
    }
  }
}
```

### 11.3 Validation Failure

```json
{
  "error": {
    "code": "validation_error",
    "message": "amount must be greater than zero."
  }
}
```

### 11.4 Not Found

```json
{
  "error": {
    "code": "not_found",
    "message": "Financial record not found."
  }
}
```

### 11.5 Conflict

```json
{
  "error": {
    "code": "conflict",
    "message": "A user with this email already exists."
  }
}
```

---

## 12. Recommended Demo Flow

For a project demo or evaluator walkthrough, test in this order:

1. `GET /health`
2. `GET /me` with admin user
3. `POST /users` to create a new analyst
4. `POST /records` as admin
5. `GET /records` as analyst
6. `GET /dashboard/summary` as viewer
7. `PATCH /users/{id}` to mark a user inactive
8. Retry an endpoint with the inactive user to show access denial

---

## 13. Notes for Submission

- This backend uses SQLite for persistence
- Authentication is mocked with `X-User-Id`
- The design focuses on API structure, business rules, validation, access control, and dashboard aggregation
- This document can be uploaded directly to Google Drive or copied into Google Docs
