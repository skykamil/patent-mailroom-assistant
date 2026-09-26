from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models.correspondence import Correspondence
from app.db.models.document import Document
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
