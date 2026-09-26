from app.db.models.correspondence import Correspondence, ImportType
from app.db.models.document import Document
from tests.integration.db import TestSessionLocal

def test_correspondence_has_documents():
    db = TestSessionLocal()
    try:
        correspondence = Correspondence(import_type=ImportType.DIRECT_UPLOAD)
        db.add(correspondence)
        db.flush()
        document = Document(
            correspondence=correspondence,
            original_filename="Office_Action.pdf",
            storage_path="data/uploads/test-office-action.pdf",
            mime_type="application/pdf",
            file_size=1234,
            sha256="1" * 64
        )
        db.add(document)
        db.flush()
        assert len(correspondence.documents) == 1
        assert correspondence.documents[0].original_filename == "Office_Action.pdf"
        assert document.correspondence is correspondence
    finally:
        db.rollback()
        db.close()
