from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.document import Document
from app.domain.exceptions import CaseNotFoundError
from app.domain.correspondence import ImportType
from app.repositories import correspondence_repository
from app.services import correspondence_service
from app.services.correspondence_service import IncomingDocument
from tests.integration.db import TestSessionLocal


def test_import_direct_documents_creates_correspondence_documents_and_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
    db = TestSessionLocal()
    documents = [
        IncomingDocument(
            original_filename="Office_Action.pdf",
            content=b"synthetic office action",
            mime_type="application/pdf",
        ),
        IncomingDocument(
            original_filename="Search_Report.pdf",
            content=b"synthetic search report",
            mime_type="application/pdf",
        ),
    ]
    result = None
    try:
        result = correspondence_service.import_direct_documents(
            db=db,
            documents=documents,
        )
        assert result.id is not None
        assert len(result.documents) == 2
        for db_document in result.documents:
            assert Path(db_document.storage_path).exists()
    finally:
        if result is not None:
            for db_document in result.documents:
                db.delete(db_document)
            db.delete(result)
            db.commit()
        db.close()


def test_import_direct_documents_cleans_up_on_commit_error(tmp_path: Path, monkeypatch):
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)

        def fail_commit():
            db.flush()
            raise RuntimeError("synthetic commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        documents = [
            IncomingDocument(
                original_filename="Office_Action.pdf",
                content=b"synthetic office action",
                mime_type="application/pdf",
            )
        ]
        correspondence_count_before = db.scalar(select(func.count()).select_from(Correspondence))
        document_count_before = db.scalar(select(func.count()).select_from(Document))
        with pytest.raises(RuntimeError):
            correspondence_service.import_direct_documents(
                db=db,
                documents=documents,
            )
        correspondence_count_after = db.scalar(select(func.count()).select_from(Correspondence))
        document_count_after = db.scalar(select(func.count()).select_from(Document))
        assert correspondence_count_after == correspondence_count_before
        assert document_count_after == document_count_before
        assert list(tmp_path.iterdir()) == []
    finally:
        db.close()


def test_import_cleanup_continues_when_file_deletion_fails(tmp_path: Path, monkeypatch, caplog):
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        documents = [
            IncomingDocument(
                original_filename="Office_Action.pdf",
                content=b"synthetic office action",
                mime_type="application/pdf",
            ),
            IncomingDocument(
                original_filename="Search_Report.pdf",
                content=b"synthetic search report",
                mime_type="application/pdf",
            ),
        ]

        def fail_commit():
            db.flush()
            raise RuntimeError("synthetic import failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        delete_attempts: list[str] = []
        original_delete_file = correspondence_service.local_storage.delete_file

        def fail_first_delete(storage_path: str):
            delete_attempts.append(storage_path)
            if len(delete_attempts) == 1:
                raise OSError("synthetic cleanup failure")
            original_delete_file(storage_path)

        monkeypatch.setattr(correspondence_service.local_storage, "delete_file", fail_first_delete)
        with pytest.raises(RuntimeError, match="synthetic import failure"):
            correspondence_service.import_direct_documents(
                db=db,
                documents=documents,
            )
        assert len(delete_attempts) == 2
        assert "synthetic cleanup failure" in caplog.text
    finally:
        db.close()


def test_import_direct_documents_missing_case(tmp_path: Path, monkeypatch):
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        document = IncomingDocument(
            original_filename="Office_Action.pdf",
            content=b"synthetic office action",
            mime_type="application/pdf",
        )
        max_case_id = db.scalar(select(func.max(Case.id))) or 0
        missing_case_id = max_case_id + 1
        with pytest.raises(CaseNotFoundError):
            correspondence_service.import_direct_documents(
                db=db,
                documents=[document],
                case_id=missing_case_id,
            )
        assert list(tmp_path.iterdir()) == []
    finally:
        db.close()


def test_get_correspondence_by_source_sha256():
    db = TestSessionLocal()
    try:
        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            source_sha256="a" * 64
        )
        db.add(correspondence)
        db.flush()
        result = correspondence_repository.get_correspondence_by_source_sha256(db, "a" * 64)
        assert result is not None
        assert result.id == correspondence.id
        assert result.source_sha256 == "a" * 64
    finally:
        db.rollback()
        db.close()


def test_import_email_creates_correspondence(tmp_path: Path, monkeypatch):
    db = TestSessionLocal()
    result = None
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        fixture_path = Path(__file__).resolve().parents[1]/"fixtures"/"emails"/"PAT-CN-001_office_action_4mo.eml"
        raw_email = fixture_path.read_bytes()
        result = correspondence_service.import_email(
            db=db,
            raw_email=raw_email,
            original_filename=fixture_path.name
        )
        assert result.created is True
        correspondence = result.correspondence
        assert correspondence.import_type == ImportType.EMAIL
        assert correspondence.source_sha256 == sha256(raw_email).hexdigest()
        assert correspondence.source_storage_path is not None
        assert Path(correspondence.source_storage_path).exists()
        assert len(correspondence.documents) == 2
        document_name = {document.original_filename for document in correspondence.documents}
        assert document_name == {"Agent_Letter.pdf", "Office_Action.pdf"}
        for document in correspondence.documents:
            assert Path(document.storage_path).exists()
    finally:
        if result is not None:
            correspondence = result.correspondence
            for document in correspondence.documents:
                db.delete(document)
            db.delete(correspondence)
            db.commit()
        db.close()


def test_import_email_returns_existing_correspondence_for_duplicate(tmp_path: Path, monkeypatch):
    first_result = None
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        fixture_path = Path(__file__).resolve().parents[1]/"fixtures"/"emails"/"PAT-CN-001_office_action_4mo.eml"
        raw_email = fixture_path.read_bytes()
        first_result = correspondence_service.import_email(
            db=db,
            raw_email=raw_email,
            original_filename=fixture_path.name,
        )
        second_result = correspondence_service.import_email(
            db=db,
            raw_email=raw_email,
            original_filename=fixture_path.name,
        )
        assert first_result.created is True
        assert second_result.created is False
        assert second_result.correspondence.id == first_result.correspondence.id
        assert len(list(tmp_path.iterdir())) == 3
    finally:
        if first_result is not None:
            correspondence = first_result.correspondence
            for document in correspondence.documents:
                db.delete(document)
            db.delete(correspondence)
            db.commit()
        db.close()


def test_import_email_cleans_up_on_commit_error(tmp_path: Path, monkeypatch):
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)

        def fail_commit():
            db.flush()
            raise RuntimeError("synthetic email import failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        fixture_path = Path(__file__).resolve().parents[1]/"fixtures"/"emails"/"PAT-CN-001_office_action_4mo.eml"
        raw_email = fixture_path.read_bytes()
        correspondence_count_before = db.scalar(select(func.count()).select_from(Correspondence))
        document_count_before = db.scalar(select(func.count()).select_from(Document))
        with pytest.raises(RuntimeError, match="synthetic email import failure"):
            correspondence_service.import_email(
                db=db,
                raw_email=raw_email,
                original_filename=fixture_path.name,
            )
        correspondence_count_after = db.scalar(select(func.count()).select_from(Correspondence))
        document_count_after = db.scalar(select(func.count()).select_from(Document))
        assert correspondence_count_after == correspondence_count_before
        assert document_count_after == document_count_before
        assert list(tmp_path.iterdir()) == []
    finally:
        db.close()


def test_import_email_missing_case(tmp_path: Path, monkeypatch):
    db = TestSessionLocal()
    try:
        monkeypatch.setattr(correspondence_service.local_storage, "UPLOAD_DIR", tmp_path)
        max_case_id = db.scalar(select(func.max(Case.id))) or 0
        missing_case_id = max_case_id + 1
        fixture_path = Path(__file__).resolve().parents[1]/"fixtures"/"emails"/"PAT-CN-001_office_action_4mo.eml"
        raw_email = fixture_path.read_bytes()
        with pytest.raises(CaseNotFoundError):
            correspondence_service.import_email(
                db=db,
                raw_email=raw_email,
                original_filename=fixture_path.name,
                case_id=missing_case_id,
            )
        assert list(tmp_path.iterdir()) == []
    finally:
        db.close()
