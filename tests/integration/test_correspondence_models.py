from uuid import uuid4

from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.file import File
from tests.integration.db import TestSessionLocal


def test_correspondence_has_files():
    db = TestSessionLocal()

    try:
        case = Case(
            internal_reference=f"PAT-CN-{uuid4().int}"
        )
        db.add(case)
        db.flush()

        correspondence = Correspondence(
            case_id=case.id,
            submission_id=str(uuid4())
        )
        db.add(correspondence)
        db.flush()

        file = File(
            correspondence=correspondence,
            filename="Office_Action.pdf",
            storage_key="data/uploads/test-office-action.pdf",
            mime_type="application/pdf",
            size_bytes=1234,
            source_file_id=str(uuid4())
        )
        db.add(file)
        db.flush()

        assert correspondence.case_id == case.id
        assert len(correspondence.files) == 1
        assert correspondence.files[0].filename == "Office_Action.pdf"
        assert file.correspondence is correspondence

    finally:
        db.rollback()
        db.close()
