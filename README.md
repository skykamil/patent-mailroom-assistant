# Patent Mailroom Assistant

An educational backend project for processing patent correspondence, built with Python, FastAPI, SQLAlchemy and PostgreSQL.

The intended workflow is to import an email, extract information from its contents and attachments, and prepare proposed updates for human review. The current implementation covers the case creation, retrieval, partial update and deletion foundation. Email processing, AI analysis and approval workflows are not implemented yet.

## Current functionality

- Create patent cases through a REST API.
- Retrieve a patent case by its database ID.
- Partially update case data while leaving unspecified fields unchanged.
- Delete cases that are not referenced by related records.
- Prevent deletion of cases that are still in use.
- Derive the jurisdiction from the internal reference, for example `PAT-CN-001` → `CN`.
- Validate the internal reference format and text field lengths.
- Store optional application, publication, grant and agent reference data.
- Prevent duplicate internal references and duplicate application numbers within the same jurisdiction.
- Return HTTP `409` for supported uniqueness conflicts, including conflicts detected during database writes.
- Store correspondence records and document metadata as the foundation for future email and direct-document imports.
- Manage database changes with Alembic migrations.


The database also includes a case relationship model with `direct_parent` and `priority` relationship types. Relationship management is not exposed through the API yet.

## Technology

- Python 3.12+
- FastAPI and Pydantic
- SQLAlchemy and Psycopg
- PostgreSQL 17, running locally through Docker Compose
- Alembic
- pytest and HTTPX

## Project structure

| Directory | Responsibility |
| --- | --- |
| `app/api/` | HTTP routes and database session dependency |
| `app/core/` | Application settings |
| `app/db/` | Database engine, sessions and SQLAlchemy models |
| `app/domain/` | Reference validation, jurisdiction rules and domain exceptions |
| `app/repositories/` | Database queries and adding records to the session |
| `app/schemas/` | Request validation and response schemas |
| `app/services/` | Case creation, retrieval, update and deletion, transaction handling and conflict translation |
| `alembic/` | Database migrations |
| `tests/unit/` | Reference rule and health endpoint tests |
| `tests/integration/` | API and service tests using a separate PostgreSQL database |

## Local setup

Requirements: Python 3.12+, Git and Docker with Docker Compose. The commands below use a macOS/Linux shell. Run them from the repository root after cloning.

### 1. Install the project

```bash
git clone https://github.com/skykamil/patent-mailroom-assistant.git
cd patent-mailroom-assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### 2. Start PostgreSQL

```bash
docker compose up -d db
docker compose exec db pg_isready -U patent_mailroom -d patent_mailroom
```

Wait for `accepting connections` before continuing. If necessary, repeat the second command.

On first initialization, Docker Compose creates the `patent_mailroom` database. Data is stored in the `postgres_data` volume. Port `5432` must be available on the host.

The bundled database credentials and port configuration are for local development, not a production deployment.

### 3. Apply migrations

```bash
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

- Interactive API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health endpoint: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

The health endpoint returns `{"status":"ok"}`. It checks that the API responds; it does not check database connectivity.

## Configuration

Settings are defined in `app/core/config.py` and can be overridden through environment variables.

| Variable | Default |
| --- | --- |
| `APP_NAME` | `Patent Mailroom Assistant` |
| `ENVIRONMENT` | `development` |
| `DATABASE_URL` | `postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom` |

The current settings do not automatically load a `.env` file. Use shell environment variables when overriding the defaults. Use the same database URL for the application and its migrations.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic API health check |
| `POST` | `/cases` | Create a patent case |
| `GET` | `/cases/{case_id}` | Retrieve a patent case by database ID |
| `PATCH` | `/cases/{case_id}` | Partially update a patent case |
| `DELETE` | `/cases/{case_id}` | Delete a patent case |

### Create a case

```bash
curl -i -X POST http://127.0.0.1:8000/cases \
  -H 'Content-Type: application/json' \
  -d '{
    "internal_reference": "PAT-CN-001",
    "application_number": "123456789",
    "application_date": "2025-10-01",
    "agent_reference": "SYNTHETIC-AGENT-001"
  }'
```

This example uses synthetic data. Only `internal_reference` is required. The jurisdiction is derived by the application rather than supplied in the request.

| Status | Meaning |
| --- | --- |
| `200 OK` | Case retrieved successfully |
| `201 Created` | Case created; the response includes its database ID and jurisdiction |
| `404 Not Found` | Case with the requested ID does not exist |
| `409 Conflict` | A uniqueness conflict occurred, or the case cannot be deleted because it is in use |
| `422 Unprocessable Content` | Request validation failed |

Repeating the example without changing its identifiers returns `409`. The same application number can be used in different jurisdictions. Cases may also omit the application number.

### Get a case

```bash
curl -i http://127.0.0.1:8000/cases/1
```

If the case exists, the API returns `200 OK` with the case data.

If the case does not exist, the API returns `404 Not Found`.

### Update a case

```bash
curl -i -X PATCH http://127.0.0.1:8000/cases/1 \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_reference": "UPDATED-REF"
  }'
```

Only fields included in the request are updated. Sending an optional field as `null` clears that field.

### Delete a case

```bash
curl -i -X DELETE http://127.0.0.1:8000/cases/1
```

A case that is not in use is deleted with `204 No Content`. If the case is referenced by another database record, the API returns `409 Conflict`.

## Tests

The integration tests use a separate database, `patent_mailroom_test`, on the same local PostgreSQL server. Docker Compose does not create this database automatically.

With PostgreSQL running, create the test database once:

```bash
docker compose exec db createdb -U patent_mailroom patent_mailroom_test
```

If the database already exists, skip that command. Apply migrations to it:

```bash
DATABASE_URL='postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom_test' alembic upgrade head
```

This override applies only to that migration command. The integration tests currently define their own fixed test database URL in `tests/integration/db.py`.

Run the full suite:

```bash
python -m pytest -q
```

Run the tests that do not require a running database:

```bash
python -m pytest tests/unit -q
```

Tests cover reference rules, request validation, case creation, retrieval, partial update and deletion, 404 handling, jurisdiction-scoped uniqueness, conflicts detected during database writes, and the Correspondence-to-Document relationship. The write-conflict tests bypass the preliminary lookup to exercise database constraint handling; they do not simulate concurrent requests.

After adding migrations, apply them to both the application and test databases before running integration tests.

## Stopping the local environment

Stop the API with `Ctrl+C`, then stop PostgreSQL:

```bash
docker compose down
```

The database volume is retained. Adding `-v` would delete it and its data.
