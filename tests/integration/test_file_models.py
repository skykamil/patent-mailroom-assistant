from uuid import uuid4

from app.db.models.case import Case
from app.db.models.file import File
from app.domain.doc_type import DocType
from tests.integration.db import TestSessionLocal


def test_case_has_files():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"PAT-CN-{uuid4().int}")
        db.add(case)
        db.flush()

        file = File(
            case=case,
            submission_id=str(uuid4()),
            filename="Office_Action.pdf",
            storage_key="data/uploads/test-office-action.pdf",
            mime_type="application/pdf",
            size_bytes=1234,
            client_file_id=str(uuid4()),
        )
        db.add(file)
        db.flush()

        assert file.case_id == case.id
        assert len(case.files) == 1
        assert case.files[0].filename == "Office_Action.pdf"
        assert file.case is case

    finally:
        db.rollback()
        db.close()


def test_file_doc_type_defaults_to_other():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"PAT-CN-{uuid4().int}")
        file = File(
            case=case,
            submission_id=str(uuid4()),
            filename="Unknown.pdf",
            storage_key="data/uploads/test-unknown.pdf",
            mime_type="application/pdf",
            size_bytes=1234,
            client_file_id=str(uuid4()),
        )
        db.add(file)
        db.flush()
        db.refresh(file)

        assert file.doc_type == DocType.OTHER

    finally:
        db.rollback()
        db.close()


def test_file_keeps_explicit_doc_type():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"PAT-CN-{uuid4().int}")
        file = File(
            case=case,
            submission_id=str(uuid4()),
            doc_type=DocType.OFFICE_ACTION,
            filename="Office_Action.pdf",
            storage_key="data/uploads/test-office-action.pdf",
            mime_type="application/pdf",
            size_bytes=1234,
            client_file_id=str(uuid4()),
        )
        db.add(file)
        db.flush()
        db.refresh(file)

        assert file.doc_type == DocType.OFFICE_ACTION

    finally:
        db.rollback()
        db.close()
