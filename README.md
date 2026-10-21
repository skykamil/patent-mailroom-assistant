# Patent Mailroom Assistant

An educational backend for importing patent correspondence and reviewing proposed analysis results, built with Python, FastAPI, SQLAlchemy and PostgreSQL.

Automatic analysis generation, AI integration and deadline calculation are not implemented yet.

## Current functionality

### Cases

- Create, retrieve, partially update and delete patent cases through the REST API.
- Prevent deletion of cases referenced by related records.
- Validate internal references and text field lengths, and derive jurisdiction from the reference, for example `PAT-CN-001` → `CN`.
- Store optional application, publication, grant and agent reference data.
- Enforce unique internal references and unique application numbers within each jurisdiction, returning `409 Conflict` for supported uniqueness conflicts.

### Analysis

- Store at most one `Analysis` per `Correspondence`, containing proposed case identifiers, Office Action type, relevant dates and timestamps.

### Tasks

- Tasks belong directly to a source `Correspondence`.
- Only one primary task of each type is allowed per correspondence.

### Storage and database

- Store files locally under generated filenames.
- Record document file sizes and SHA-256 hashes.
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
| `app/domain/` | Domain enums, reference validation, jurisdiction rules and domain exceptions |
| `app/parsers/` | Deterministic parsing of incoming `.eml` messages, email metadata, body text and MIME attachments |
| `app/repositories/` | Database queries and adding records to the session |
| `app/schemas/` | Request validation and response schemas |
| `app/services/` | Case operations, analysis result handling, transaction handling |
| `app/storage/` | Local filesystem storage and file cleanup |
| `alembic/` | Database migrations |
| `tests/unit/` | Reference rule, health endpoint, local storage and email parser tests |
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

### File storage

Local storage uses `data/uploads/`, relative to the application's working directory.

The storage path is currently defined in `app/storage/local_storage.py`; it is not an environment-variable setting.

These files are stored separately from the PostgreSQL Docker volume. Removing the database volume does not remove uploaded files, and removing uploaded files does not remove their database records.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic API health check |
| `POST` | `/cases` | Create a patent case |
| `GET` | `/cases/{case_id}` | Retrieve a patent case by database ID |
| `PATCH` | `/cases/{case_id}` | Partially update a patent case |
| `DELETE` | `/cases/{case_id}` | Delete a patent case |
| `GET` | `/correspondences/{correspondence_id}/analysis` | Retrieve the `Analysis` for a `Correspondence` |

The examples below use `1` as a placeholder database ID. Replace case IDs in `/cases/1` with the `id` returned when creating a case.

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

### Case response statuses

| Status | Meaning |
| --- | --- |
| `200 OK` | Case retrieved or updated successfully |
| `201 Created` | Case created; the response includes its database ID and jurisdiction |
| `204 No Content` | Case deleted successfully |
| `404 Not Found` | Case with the requested ID does not exist |
| `409 Conflict` | A uniqueness conflict occurred, or the case cannot be deleted because it is in use |
| `422 Unprocessable Content` | Request validation failed |

### Get analysis

The stored analysis for a `Correspondence` can be retrieved by its correspondence ID:

```bash
curl -i http://127.0.0.1:8000/correspondences/1/analysis
```

This endpoint returns the existing `Analysis` without modifying it.

| Status | Meaning |
| --- | --- |
| `200 OK` | The analysis was retrieved successfully |
| `404 Not Found` | The correspondence does not exist, or it has no analysis yet |

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

Tests cover:

- **Cases:** reference rules, request validation, creation, retrieval, partial updates, deletion, missing-record handling, jurisdiction-scoped uniqueness and conflicts detected during database writes.
- **Storage:** local file storage and the `Correspondence`–`Document` relationship.
- **Email parsing:** metadata, plain-text and HTML-only body extraction, MIME attachments including attached emails and multipart content, unnamed attachments, case-insensitive headers and a synthetic email fixture. Invalid-input tests cover empty content, plain text, PDF content and unsupported character encodings.

After adding migrations, apply them to both the application and test databases before running integration tests.

## Stopping the local environment

Stop the API with `Ctrl+C`, then stop PostgreSQL:

```bash
docker compose down
```

The database volume is retained. Adding `-v` would delete it and its data.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
