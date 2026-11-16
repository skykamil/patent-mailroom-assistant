# Patent Mailroom Assistant

An educational backend for handling incoming patent correspondence: take an email or loose files, attach them to a patent case, and record the resulting tasks after human review. Built with Python, FastAPI, SQLAlchemy and PostgreSQL.

This is a personal learning project. All sample data is synthetic.

## Status

The project is in progress. The table below shows what the code does today.

| Area | State |
| --- | --- |
| Case CRUD through the REST API | Working |
| File preparation (`POST /reviews/prepare`), including splitting `.eml` attachments | Working |
| Database schema for cases, files, tasks and case relationships | In place |
| File selection with document types, case lookup by reference, local file storage | Implemented and tested as services, not exposed through the API yet |
| Saving files and tasks to a case | Not implemented |
| Upload limits (file count, size, allowed types) | Not implemented |
| Automatic analysis, AI integration, deadline calculation | Not implemented |
| Frontend, authentication | Not implemented |

### Planned

- **v0.1** – save selected files (each with a document type) and manually added tasks to a case in one transaction, upload limits, a simple frontend, CI.
- **v0.2** – LLM analysis of selected document types that proposes tasks for human review.

## Current functionality

### Cases

- Create, retrieve, partially update and delete patent cases.
- Validate the internal reference format: `PAT-<two uppercase letters>-<digits>`, for example `PAT-CN-001`.
- Enforce unique internal references, returning `409 Conflict` for duplicates. Application numbers may repeat across cases.
- Store optional application, publication and grant numbers.
- Refuse to delete a case that is referenced by files, tasks or case relationships.

### File preparation

`POST /reviews/prepare` accepts uploaded files together with a client-generated UUID for each one and returns the list of files a user can choose from.

- Every uploaded file is listed as-is.
- For a `.eml` file, each attachment is additionally listed as a separate entry, right after the email it came from.
- Attachment IDs are deterministic (UUIDv5 derived from the email's ID and the attachment position), so sending the same email with the same ID always yields the same IDs.
- The endpoint is stateless: nothing is written to the database or to disk.

### Email parsing

The `.eml` parser reads the subject, sender, date, message ID, body text (plain text preferred, HTML as fallback) and attachments, including attached emails and multipart attachments. Attachments without a filename get a generated name. Content that is not an email, or that uses an unsupported character encoding, is rejected.

### Implemented but not exposed through the API

- **File selection** – check the user's selection (file ID plus document type) against the prepared files; reject empty selections, duplicate IDs and unknown IDs.
- **Case lookup by reference** – find a case by internal reference, ignoring letter case and surrounding spaces.
- **Local storage** – save a file under a generated name in `data/uploads/` and return its path, size and SHA-256 hash; remove partially written files on failure.

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
| `app/api/` | HTTP routes and the database session dependency |
| `app/core/` | Application settings |
| `app/db/` | Database engine, sessions and SQLAlchemy models |
| `app/domain/` | Domain enums (document types, task types), reference rules and domain exceptions |
| `app/parsers/` | Deterministic parsing of `.eml` messages |
| `app/repositories/` | Database queries and adding records to the session |
| `app/schemas/` | Request validation and response schemas |
| `app/services/` | Case operations (`case_service`) and file preparation and selection (`review_service`) |
| `app/storage/` | Local filesystem storage |
| `alembic/` | Database migrations |
| `tests/unit/` | Tests that run without a database |
| `tests/integration/` | API, service and model tests using a separate PostgreSQL database |
| `tests/fixtures/` | Synthetic sample email |

## Local setup

Requirements: Python 3.12+, Git and Docker with Docker Compose. The commands below use a macOS/Linux shell.

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

On first start, Docker Compose creates the `patent_mailroom` database. Data is stored in the `postgres_data` volume. Port `5432` must be free on the host.

The bundled credentials and port mapping are for local development only.

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

The health endpoint returns `{"status":"ok"}`. It confirms that the API responds; it does not check the database connection.

## Configuration

Settings are defined in `app/core/config.py` and can be overridden with environment variables.

| Variable | Default |
| --- | --- |
| `APP_NAME` | `Patent Mailroom Assistant` |
| `ENVIRONMENT` | `development` |
| `DATABASE_URL` | `postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom` |

A `.env` file is not loaded automatically; use shell environment variables. The application and Alembic read the same `DATABASE_URL`.

The local storage directory, `data/uploads/` relative to the working directory, is set in `app/storage/local_storage.py` and is not configurable through the environment.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic API health check |
| `POST` | `/cases` | Create a patent case |
| `GET` | `/cases/{case_id}` | Retrieve a case by database ID |
| `PATCH` | `/cases/{case_id}` | Partially update a case |
| `DELETE` | `/cases/{case_id}` | Delete a case |
| `POST` | `/reviews/prepare` | List uploaded files and email attachments for review |

### Cases

Create a case:

```bash
curl -i -X POST http://127.0.0.1:8000/cases \
  -H 'Content-Type: application/json' \
  -d '{
    "internal_reference": "PAT-CN-001",
    "application_number": "202611111111.1"
  }'
```

```json
{
  "id": 1,
  "internal_reference": "PAT-CN-001",
  "application_number": "202611111111.1",
  "publication_number": null,
  "grant_number": null
}
```

Only `internal_reference` is required. `application_number`, `publication_number` and `grant_number` are optional, up to 50 characters each.

Retrieve, update and delete a case, using the `id` returned on creation:

```bash
curl -i http://127.0.0.1:8000/cases/1

curl -i -X PATCH http://127.0.0.1:8000/cases/1 \
  -H 'Content-Type: application/json' \
  -d '{"publication_number": "CN123456789A"}'

curl -i -X DELETE http://127.0.0.1:8000/cases/1
```

`PATCH` changes only the fields sent in the request; sending `null` clears a field. The internal reference cannot be changed, and unknown fields are rejected.

| Status | Meaning |
| --- | --- |
| `200 OK` | Case retrieved or updated |
| `201 Created` | Case created |
| `204 No Content` | Case deleted |
| `404 Not Found` | No case with the requested ID |
| `409 Conflict` | The internal reference already exists, or the case cannot be deleted because it is in use |
| `422 Unprocessable Content` | Request validation failed |

### File preparation

The request is `multipart/form-data` with two repeated fields:

| Field | Content |
| --- | --- |
| `files` | One or more files |
| `file_ids` | One UUID per file, in the same order, each unique within the request |

Example using the synthetic email from the test fixtures:

```bash
curl -X POST http://127.0.0.1:8000/reviews/prepare \
  -F 'files=@tests/fixtures/emails/PAT-CN-001_office_action_4mo.eml;type=message/rfc822' \
  -F 'file_ids=3f2b8c1e-5d47-4a9b-9c0e-1a2b3c4d5e6f'
```

```json
{
  "files": [
    {
      "file_id": "3f2b8c1e-5d47-4a9b-9c0e-1a2b3c4d5e6f",
      "source_file_id": "3f2b8c1e-5d47-4a9b-9c0e-1a2b3c4d5e6f",
      "attachment_index": null,
      "filename": "PAT-CN-001_office_action_4mo.eml",
      "mime_type": "message/rfc822",
      "size_bytes": 175518
    },
    {
      "file_id": "7f7a08d3-d9a2-550d-b680-a90a4a07c568",
      "source_file_id": "3f2b8c1e-5d47-4a9b-9c0e-1a2b3c4d5e6f",
      "attachment_index": 0,
      "filename": "Agent_Letter.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 44493
    },
    {
      "file_id": "29adc59d-cafd-5d7a-ac16-c02fd9f45d85",
      "source_file_id": "3f2b8c1e-5d47-4a9b-9c0e-1a2b3c4d5e6f",
      "attachment_index": 1,
      "filename": "Office_Action.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 82771
    }
  ]
}
```

| Response field | Meaning |
| --- | --- |
| `file_id` | The ID sent by the client, or a generated ID for an email attachment |
| `source_file_id` | ID of the uploaded file this entry comes from; equal to `file_id` for uploaded files |
| `attachment_index` | Zero-based position of the attachment in its email; `null` for uploaded files |
| `filename`, `mime_type`, `size_bytes` | File metadata |

A file is treated as an email when its name ends with `.eml`, regardless of letter case.

| Status | Meaning |
| --- | --- |
| `200 OK` | File list returned |
| `422 Unprocessable Content` | A field is missing, the numbers of files and IDs differ, an ID is repeated, or a `.eml` file is not a valid email |

There are no limits on file count, size or type yet.

## Data model

| Table | Content |
| --- | --- |
| `cases` | Internal reference (unique) and optional application, publication and grant numbers |
| `files` | A stored file belonging to a case: document type, filename, MIME type, storage key, size and a unique client file ID |
| `tasks` | A task belonging to a case: task type, start date, due date, a flag for manually adjusted dates and an optional proposal ID |
| `case_relationships` | A `direct_parent` or `priority` link between two cases |

Files and tasks belong directly to a case. Both carry a `submission_id` that groups the records created together.

- **Document types:** `office_action`, `agent_letter`, `search_report`, `claims`, `specification`, `submission`, `invoice`, `official_letter`, `reference`, `other` (default), `eml_communication_agent`, `eml_review_communication_agent`, `eml_review_office_action`, `eml_reminder`.
- **Task types:** `office_action` and `office_action_1mo` to `office_action_6mo`.

No endpoint writes to `files`, `tasks` or `case_relationships` yet.

## Tests

The unit tests need no database:

```bash
python -m pytest tests/unit -q
```

The integration tests use a separate database, `patent_mailroom_test`, on the same local PostgreSQL server. Docker Compose does not create it. With PostgreSQL running, create it once and apply the migrations:

```bash
docker compose exec db createdb -U patent_mailroom patent_mailroom_test

DATABASE_URL='postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom_test' alembic upgrade head
```

Run the full suite:

```bash
python -m pytest -q
```

The test database URL is fixed in `tests/integration/db.py`. After adding a migration, apply it to both databases before running the integration tests.

Tests cover:

- **Cases:** reference rules, request validation, creation, retrieval, partial updates, deletion, missing records, lookup by reference and conflicts detected during database writes.
- **File preparation:** single and multiple files, attachment extraction, stable attachment IDs, mismatched or repeated IDs and invalid emails.
- **File selection:** ordering, skipped files, empty selections, duplicate and unknown IDs.
- **Email parsing:** metadata, plain-text and HTML-only bodies, attached emails, multipart and unnamed attachments, case-insensitive headers, a synthetic email fixture and invalid input.
- **Models and storage:** case–file and case–task relationships, the default document type, and local file storage including cleanup after a failed write.

## Stopping the local environment

Stop the API with `Ctrl+C`, then stop PostgreSQL:

```bash
docker compose down
```

The database volume is kept. Adding `-v` would delete it together with its data.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.