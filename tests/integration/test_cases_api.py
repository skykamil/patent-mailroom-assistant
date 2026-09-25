from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_db
from app.db.models.case import Case
from app.main import app

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