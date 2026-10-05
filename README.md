# Patent Mailroom Assistant

An educational backend project for processing patent correspondence, built with Python, FastAPI, SQLAlchemy and PostgreSQL.

The intended workflow is to import an email, extract information from its contents and attachments, and prepare proposed updates for human review. The current implementation covers the case CRUD foundation, correspondence and document models, local file storage, direct-document import through the HTTP API, deterministic MIME parsing of `.eml` messages and their attachments, transactional email import through the HTTP API with source-file storage, attachment extraction and duplicate detection, and the database model, service layer and HTTP API for storing, retrieving, updating and approving prepared analysis results. Automatic analysis generation, AI integration and task creation from approved analyses are not implemented yet.

## Current functionality

### Cases

- Create, retrieve, partially update and delete patent cases through the REST API.
- Prevent deletion of cases referenced by related records.
- Validate internal references and text field lengths, and derive jurisdiction from the reference, for example `PAT-CN-001` → `CN`.
- Store optional application, publication, grant and agent reference data.
- Enforce unique internal references and unique application numbers within each jurisdiction, returning `409 Conflict` for supported uniqueness conflicts.

### Correspondence import

- Import one or more documents through the direct-upload API, creating a `Correspondence` and related `Document` records.
- Parse and import `.eml` messages, extracting email metadata, plain-text body content and MIME attachments.
- Store the original `.eml` file and its SHA-256 source hash, with attachments stored as related `Document` records.
- Return the existing `Correspondence` for byte-identical email imports without changing its case association.
- Reject invalid email content, unsupported character encodings and invalid attachment metadata before storing files or database records.

### Analysis

- Store at most one `Analysis` per `Correspondence`, containing proposed case identifiers, event classification, Office Action type, relevant dates and timestamps.
- Create, retrieve, replace and approve a prepared analysis result through the HTTP API.
- Track analysis review state as `pending_review` or `approved`, including the approval timestamp.
- Prevent further edits after an analysis has been approved.
- Roll back failed analysis writes and serialize concurrent saves for the same correspondence to prevent duplicate records.
- Accept analysis data supplied by the client. Automatic extraction, deadline calculation, AI integration and task creation from approved analyses are not implemented yet.

### Events and tasks

- Store case-level `Event` records representing concrete business events, with an event type and creation timestamp.
- Allow an editable `Analysis` to keep an event-selection decision as `unresolved`, `new_event` or `existing_event`.
- Store an optional `event_id` on an analysis. Multiple analyses can reference the same event.
- Validate existing-event selections against event existence, case ownership and event type before saving the review decision.
- Prevent changes to the event-selection decision after the analysis has been approved.
- Store `Task` records linked to an `Event`, including task type, name, due date and whether the task is primary.
- Prevent duplicate primary tasks of the same type for the same event while allowing multiple non-primary tasks.
- Automatic event matching, event creation during approval and task creation or update from approved analyses are not implemented yet.

### Storage and database

- Store uploaded documents and email source files locally under generated filenames.
- Record document file sizes and SHA-256 hashes.
- Roll back database changes and attempt to remove files written during a failed import, logging any file cleanup errors.
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
| `app/services/` | Case operations, correspondence import orchestration, analysis result handling, transaction handling and cleanup |
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

Uploaded documents, email attachments and original `.eml` files are stored in `data/uploads/`, relative to the application's working directory. Run the API from the repository root to use this location consistently.

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
| `POST` | `/correspondences/direct-upload` | Import one or more documents and create a `Correspondence` record |
| `POST` | `/correspondences/email-import` | Import an `.eml` message and create or return a `Correspondence` record |
| `GET` | `/correspondences/{correspondence_id}/analysis` | Retrieve the `Analysis` for a `Correspondence` |
| `PUT` | `/correspondences/{correspondence_id}/analysis` | Create or replace the `Analysis` for a `Correspondence` |
| `POST` | `/correspondences/{correspondence_id}/analysis/approve` | Approve the `Analysis` for a `Correspondence` |

The examples below use `1` as a placeholder database ID. Replace case IDs in `/cases/1` and `case_id=1` with the `id` returned when creating a case. Replace the correspondence ID in `/correspondences/1/analysis` with the `id` returned by an import.

The examples demonstrate individual operations. If you want to associate an import with a case, keep that case instead of running the deletion example first.

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

### Direct document upload

The PDF filenames below are examples, not bundled files. Replace them with paths to your own test documents.

```bash
curl -i -X POST http://127.0.0.1:8000/correspondences/direct-upload \
  -F 'files=@Office_Action.pdf' \
  -F 'files=@Search_Report.pdf'
```

To associate a new import with an existing case, include its database ID as a form field:

```bash
curl -i -X POST http://127.0.0.1:8000/correspondences/direct-upload \
  -F 'files=@Office_Action.pdf' \
  -F 'case_id=1'
```

Each successful request creates a new `Correspondence` and related `Document` records. Direct document uploads do not use the email import's duplicate detection.

| Status | Meaning |
| --- | --- |
| `201 Created` | Documents imported successfully |
| `404 Not Found` | The supplied case ID does not exist |
| `422 Unprocessable Content` | Request validation failed, including invalid document metadata |

### Email import

The repository includes a synthetic `.eml` fixture. Run this example from the repository root:

```bash
curl -i -X POST http://127.0.0.1:8000/correspondences/email-import \
  -F 'file=@tests/fixtures/emails/PAT-CN-001_office_action_4mo.eml'
```

Alternatively, to associate the email with an existing case on its first import, include the case's database ID:

```bash
curl -i -X POST http://127.0.0.1:8000/correspondences/email-import \
  -F 'file=@tests/fixtures/emails/PAT-CN-001_office_action_4mo.eml' \
  -F 'case_id=1'
```

Choose the appropriate example for the first import. Importing the same file again returns the existing `Correspondence` without changing its case association. In particular, running the second example after the first does not attach the previously imported email to a case.

Duplicate detection compares the SHA-256 hash of the original file bytes. It applies to byte-identical messages, not messages with merely similar contents.

| Status | Meaning |
| --- | --- |
| `200 OK` | A byte-identical email already exists; the existing correspondence is returned |
| `201 Created` | Email imported successfully |
| `404 Not Found` | The supplied case ID does not exist |
| `422 Unprocessable Content` | Invalid email content, unsupported character encoding or request validation failure, including invalid attachment metadata |

### Save analysis

A prepared analysis result can be stored for an existing `Correspondence`. Use the correspondence ID returned by an import:

```bash
curl -i -X PUT http://127.0.0.1:8000/correspondences/1/analysis \
  -H 'Content-Type: application/json' \
  -d '{
    "internal_reference": "PAT-CN-001",
    "jurisdiction": "CN",
    "application_number": "202611111111.1",
    "event_type": "office_action",
    "office_action_type": "Office Action 4MO",
    "document_date": "2026-09-15",
    "agent_notification_date": "2026-09-18",
    "agent_reported_due_date": "2027-01-15",
    "calculated_due_date": "2027-01-15"
  }'
```

This endpoint creates or fully replaces the editable analysis data. On an existing `Analysis`, omitted fields are reset to `null`; they do not retain their previous values. Sending an explicit `null` also clears a field.

Subsequent saves keep the same analysis record and its ID. Each `Correspondence` can have at most one `Analysis`.

A newly created analysis starts with `pending_review` status and no approval timestamp. Once approved, it can no longer be modified through this endpoint.

| Status | Meaning |
| --- | --- |
| `201 Created` | The first analysis for this correspondence was saved |
| `200 OK` | The existing analysis was replaced |
| `404 Not Found` | The correspondence does not exist |
| `409 Conflict` | The analysis has already been approved and can no longer be replaced |
| `422 Unprocessable Content` | Request validation failed, including unknown fields |

All analysis values are currently supplied by the client, including `calculated_due_date`. The application does not yet extract these values automatically, calculate deadlines or generate analysis using AI.

Saving an analysis stores proposed data only. It does not update the associated case or approve the proposed changes.

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

### Approve analysis

A reviewed analysis can be approved without a request body:

```bash
curl -i -X POST http://127.0.0.1:8000/correspondences/1/analysis/approve
```

Approval changes the analysis status from `pending_review` to `approved` and records `approved_at`.

The operation is idempotent. Approving an already approved analysis returns the existing result without changing its original approval timestamp.

After approval, the analysis can no longer be replaced through the `PUT` endpoint.

| Status | Meaning |
| --- | --- |
| `200 OK` | The analysis was approved, or had already been approved |
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
- **Storage and direct uploads:** local file storage, the `Correspondence`–`Document` relationship, document import, upload API behavior, and database rollback and file cleanup after failures.
- **Email parsing:** metadata, plain-text body extraction, MIME attachments, unnamed attachments, case-insensitive headers and a synthetic email fixture. Invalid-input tests cover empty content, plain text, PDF content and unsupported character encodings.
- **Email import:** original `.eml` storage, attachment records, byte-identical duplicate detection, missing-case validation, rollback and file cleanup. API tests cover new and duplicate imports, invalid attachment metadata, and rejection of invalid email content without creating records or files.
- **Analysis service:** creation, retrieval, replacement without duplicates, clearing stored values, timestamp updates, review-state handling, idempotent approval, prevention of edits after approval, missing-correspondence and missing-analysis handling, rollback after failed creates and updates, and concurrent first saves. Event-selection tests cover unresolved and new-event decisions, linking an existing event, clearing an earlier link, case and event-type mismatches, missing events, and prevention of changes after approval.
- **Analysis API:** `201 Created` on the first save, `200 OK` on replacement, retrieval and approval, `404 Not Found` for missing correspondences or analyses, `409 Conflict` when replacing an approved analysis, and `422 Unprocessable Content` for invalid input.

After adding migrations, apply them to both the application and test databases before running integration tests.

## Stopping the local environment

Stop the API with `Ctrl+C`, then stop PostgreSQL:

```bash
docker compose down
```

The database volume is retained. Adding `-v` would delete it and its data.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
