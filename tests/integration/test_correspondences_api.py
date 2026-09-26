from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.api.dependencies import get_db
from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.document import Document
from app.main import app
from app.services import correspondence_service
from tests.integration.db import TestSessionLocal, delete_case_by_internal_reference


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def test_direct_upload_creates_correspondence_and_documents(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
    files = [
        (
            "files",
            ("Office_Action.pdf", b"synthetic office action", "application/pdf"),
        ),
        (
            "files",
            ("Search_Report.pdf", b"synthetic search report", "application/pdf"),
        ),
    ]
    response = client.post(
        "/correspondences/direct-upload",
        files=files,
    )
    correspondence_id = response.json()["id"]
    try:
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["case_id"] is None
        assert response_data["import_type"] == "direct_upload"
        assert len(response_data["documents"]) == 2
        document_names = {
            document["original_filename"] for document in response_data["documents"]
        }
        assert document_names == {"Office_Action.pdf", "Search_Report.pdf"}
        assert len(list(tmp_path.iterdir())) == 2
    finally:
        db = TestSessionLocal()
        statement = delete(Document).where(Document.correspondence_id == correspondence_id)
        db.execute(statement)
        statement = delete(Correspondence).where(Correspondence.id == correspondence_id)
        db.execute(statement)
        db.connection()
        db.close()


def test_direct_upload_returns_404_when_case_does_not_exist(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
    db = TestSessionLocal()
    max_case_id = db.scalar(select(func.max(Case.id))) or 0
    missing_case_id = max_case_id + 1
    db.close()
    files = [
        (
            "files",
            ("Office_Action.pdf", b"synthetic office action", "application/pdf"),
        ),
    ]
    response = client.post(
        "/correspondences/direct-upload",
        files=files,
        data={"case_id": str(missing_case_id)},
        )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"Case with id {missing_case_id} not found"
    assert list(tmp_path.iterdir()) == []


def test_direct_upload_assigns_existing_case(tmp_path: Path, monkeypatch):
    delete_case_by_internal_reference("PAT-CN-920")
    correspondence_id = None
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        create_case_response = client.post(
            "/cases",
            json={
                "internal_reference": "PAT-CN-920"
            },
        )
        assert create_case_response.status_code == status.HTTP_201_CREATED
        case_id = create_case_response.json()["id"]
        files = [
            (
                "files",
                ("Office_Action.pdf", b"synthetic office action", "application/pdf"),
            ),
        ]
        upload_response = client.post(
            "/correspondences/direct-upload",
            files=files,
            data={"case_id": str(case_id)},
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        correspondence_id = upload_response.json()["id"]
        assert upload_response.json()["case_id"] == case_id
    finally:
        db = TestSessionLocal()
        try:
            if correspondence_id is not None:
                statement = delete(Document).where(Document.correspondence_id == correspondence_id)
                db.execute(statement)
                statement = delete(Correspondence).where(Correspondence.id == correspondence_id)
                db.execute(statement)
            db.commit()
        finally:
            db.close()
        delete_case_by_internal_reference("PAT-CN-920")
