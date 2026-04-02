# Finance Data Processing and Access Control Backend

A self-contained backend for a finance dashboard system with:

- Role-based access control for `viewer`, `analyst`, and `admin`
- User management with active and inactive status handling
- Financial record CRUD with filtering and validation
- Dashboard summary APIs for totals, recent activity, and monthly trends
- SQLite persistence with zero external dependencies
- Automated tests covering the main business rules

## Stack

- Python 3.11
- Standard library WSGI server via `wsgiref`
- SQLite for persistence

This implementation intentionally avoids third-party packages so it runs in a fresh environment with no install step.

## How To Run

From the project root:

```bash
python -m finance_backend
```

The API starts on `http://127.0.0.1:8000` by default.

Optional environment variables:

- `HOST` default: `127.0.0.1`
- `PORT` default: `8000`
- `FINANCE_DB_PATH` default: `data/finance.db`
- `SEED_DEMO_RECORDS` default: `true`

Example:

```bash
SEED_DEMO_RECORDS=false python -m finance_backend
```

## Deploy To Render

This repo now includes:

- [requirements.txt](d:/zorvyn_assesment/requirements.txt) for Gunicorn
- [wsgi.py](d:/zorvyn_assesment/finance_backend/wsgi.py) as the production WSGI entrypoint
- [render.yaml](d:/zorvyn_assesment/render.yaml) as a Render Blueprint

### Option 1: Fastest Path With `render.yaml`

1. Push this project to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Select the GitHub repository.
4. Render will detect [render.yaml](d:/zorvyn_assesment/render.yaml).
5. Review and create the service.

The blueprint config uses:

- `gunicorn --bind 0.0.0.0:$PORT finance_backend.wsgi:application`
- `/health` as the health check
- a persistent disk mounted at `/var/data`
- `FINANCE_DB_PATH=/var/data/finance.db`

### Option 2: Manual Render Setup

If you prefer to configure it manually in the dashboard:

- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT finance_backend.wsgi:application`
- Health Check Path: `/health`

Recommended environment variables:

- `FINANCE_DB_PATH=/var/data/finance.db`
- `SEED_DEMO_RECORDS=true`

Recommended persistent disk:

- Mount path: `/var/data`
- Size: `1 GB`

### Why A Persistent Disk Matters

This project uses SQLite. On Render, SQLite data will be lost on restart or redeploy unless you attach a persistent disk. The included blueprint already configures that for you.

## Authentication Model

Authentication is mocked through the `X-User-Id` request header. The server looks up the user in SQLite and then applies role permissions.

Seeded users on first run:

- `1` admin: `admin@finance.local`
- `2` analyst: `analyst@finance.local`
- `3` viewer: `viewer@finance.local`

Inactive users are blocked even if their role would normally allow the action.

## Access Control

- `viewer`
  - Can read dashboard summary data
  - Cannot read or modify financial records
  - Cannot manage users
- `analyst`
  - Can read financial records
  - Can read dashboard summary data
  - Cannot create, update, or delete records
  - Cannot manage users
- `admin`
  - Full access to users
  - Full access to financial records
  - Can read dashboard summary data

## API Overview

### Health and Profile

- `GET /health`
- `GET /me`

### Users

Admin only:

- `GET /users`
- `POST /users`
- `GET /users/{user_id}`
- `PATCH /users/{user_id}`

Example create payload:

```json
{
  "name": "Iris Insight",
  "email": "iris@example.com",
  "role": "analyst",
  "status": "active"
}
```

### Financial Records

- `GET /records`
- `GET /records/{record_id}`

Admin only write operations:

- `POST /records`
- `PATCH /records/{record_id}`
- `DELETE /records/{record_id}`

Supported query filters for `GET /records`:

- `type`
- `category`
- `date_from`
- `date_to`
- `min_amount`
- `max_amount`
- `search`
- `limit`
- `offset`

Example create payload:

```json
{
  "amount": 1250.75,
  "type": "income",
  "category": "Consulting",
  "date": "2026-04-02",
  "notes": "Quarterly retainer"
}
```

### Dashboard Summary

- `GET /dashboard/summary`

Supported query filters:

- `type`
- `category`
- `date_from`
- `date_to`
- `min_amount`
- `max_amount`
- `recent_limit`
- `trend_months`

Returns:

- Total income
- Total expenses
- Net balance
- Category-wise totals
- Recent activity
- Monthly trends

## Example Requests

Get current admin profile:

```bash
curl -H "X-User-Id: 1" http://127.0.0.1:8000/me
```

Create a record as admin:

```bash
curl -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d "{\"amount\": 1250, \"type\": \"income\", \"category\": \"Consulting\", \"date\": \"2026-04-02\", \"notes\": \"Client retainer\"}"
```

Read records as analyst:

```bash
curl -H "X-User-Id: 2" "http://127.0.0.1:8000/records?type=expense&limit=10"
```

Read dashboard summary as viewer:

```bash
curl -H "X-User-Id: 3" "http://127.0.0.1:8000/dashboard/summary?trend_months=6&recent_limit=5"
```

## Validation and Error Handling

The API returns structured JSON errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "date must use ISO format YYYY-MM-DD."
  }
}
```

Implemented behaviors include:

- JSON body validation
- Required field checks
- Enum validation for role, status, and record type
- ISO date validation
- Numeric amount validation
- Appropriate `400`, `401`, `403`, `404`, and `409` responses

## Project Structure

```text
finance_backend/
  app.py
  auth.py
  config.py
  database.py
  errors.py
  http.py
  router.py
  services.py
  validation.py
tests/
  test_api.py
README.md
```

## Tests

Run the automated tests with:

```bash
python -B -m unittest discover -v
```

Covered scenarios include:

- Public health endpoint
- Viewer, analyst, and admin access rules
- User deactivation behavior
- Record filtering and dashboard totals
- Validation errors for bad input

## Design Notes and Tradeoffs

- Amounts are stored as integer cents in SQLite to avoid floating-point precision issues.
- The auth model is intentionally mocked with `X-User-Id` to keep the assignment focused on backend design, business logic, and authorization.
- SQLite was chosen for simplicity and persistence, but the service and routing layers are separated enough to swap storage later.
- The server uses the Python standard library to keep setup friction low; in a production system I would likely move this to FastAPI or Django REST Framework with stronger middleware, schema tooling, and auth support.
