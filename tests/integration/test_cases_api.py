from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_db
from app.db.models.case import Case
from app.main import app
from app.services import case_service

TEST_DATABASE_URL = "postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom_test"

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

def delete_case_by_internal_reference(internal_reference: str):
    db = TestSessionLocal()
    try:
        statement = delete(Case).where(Case.internal_reference == internal_reference)
        db.execute(statement)
        db.commit()
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_case():
    delete_case_by_internal_reference("PAT-CN-900")
    try:
        response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-900",
                "application_number": "11111111.1",
                "application_date": "2025-10-01",
                "agent_reference": "CN5999628/8"
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["internal_reference"] == "PAT-CN-900"
        assert response_data["jurisdiction"] == "CN"
    finally:
        delete_case_by_internal_reference("PAT-CN-900")

def test_create_case_returns_409_when_internal_reference_exists():
    delete_case_by_internal_reference("PAT-CN-901")
    try:
        first_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-901"
            },
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        second_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-901"
            },
        )
        assert second_response.status_code == status.HTTP_409_CONFLICT
        response_data = second_response.json()
        assert response_data["detail"] == ("Case with internal reference PAT-CN-901 already exists")
    finally:
        delete_case_by_internal_reference("PAT-CN-901")

def test_create_case_returns_422_for_invalid_internal_reference():
    response = client.post(
        "/cases",
        json={
            "internal_reference": "PATCN001"
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_create_case_returns_422_when_internal_reference_is_too_long():
    response = client.post(
        "/cases",
        json={
            "internal_reference": "PAT-CN-" + "1" * 44
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_create_case_allows_same_application_number_in_different_jurisdictions():
    delete_case_by_internal_reference("PAT-CN-903")
    delete_case_by_internal_reference("PAT-EP-904")
    try:
        first_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-903",
                "application_number": "123456789"
            },
        )
        second_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-EP-904",
                "application_number": "123456789"
            },
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        assert second_response.status_code == status.HTTP_201_CREATED
    finally:
        delete_case_by_internal_reference("PAT-CN-903")
        delete_case_by_internal_reference("PAT-EP-904")

def test_create_case_returns_409_for_duplicate_application_number_in_same_jurisdiction():
    delete_case_by_internal_reference("PAT-CN-907")
    delete_case_by_internal_reference("PAT-CN-908")
    try:
        first_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-907",
                "application_number": "987654321"
            },
        )
        second_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-908",
                "application_number": "987654321"
            },
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        assert second_response.status_code == status.HTTP_409_CONFLICT
    finally:
        delete_case_by_internal_reference("PAT-CN-907")
        delete_case_by_internal_reference("PAT-CN-908")

def test_create_case_returns_409_when_internal_reference_conflict_occurs_at_database_write(monkeypatch):
    monkeypatch.setattr(
        case_service.case_repository,
        "get_case_by_internal_reference",
        lambda db, internal_reference: None
    )
    delete_case_by_internal_reference("PAT-CN-910")
    try:
        first_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-910"
            },
        )
        second_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-910"
            },
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        assert second_response.status_code == status.HTTP_409_CONFLICT
    finally:
        delete_case_by_internal_reference("PAT-CN-910")
