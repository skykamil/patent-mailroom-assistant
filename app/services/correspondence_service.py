import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence
from app.db.models.document import Document
from app.domain.correspondence import ImportType
from app.repositories import correspondence_repository, document_repository
from app.services import case_service
from app.storage import local_storage


logger = logging.getLogger(__name__)


@dataclass
class IncomingDocument:
    original_filename: str
    content: bytes
    mime_type: str


def import_direct_documents(
    db: Session,
    documents: list[IncomingDocument],
    case_id: int | None = None,
) -> Correspondence:
    saved_paths: list[str] = []
    try:
        if case_id is not None:
            case_service.get_case_by_id(db, case_id)
        correspondence = Correspondence(
            case_id=case_id,
            import_type=ImportType.DIRECT_UPLOAD,
        )
        correspondence_repository.create_correspondence(db, correspondence)
        for document in documents:
            stored_file = local_storage.save_file(
                content=document.content,
                original_filename=document.original_filename,
            )
            saved_paths.append(stored_file.storage_path)
            db_document = Document(
                correspondence=correspondence,
                original_filename=document.original_filename,
                mime_type=document.mime_type,
                storage_path=stored_file.storage_path,
                file_size=stored_file.file_size,
                sha256=stored_file.sha256,
            )
            document_repository.create_document(db, db_document)
        db.commit()
    except Exception:
        db.rollback()
        for storage_path in saved_paths:
            try:
                local_storage.delete_file(storage_path)
            except OSError:
                logger.exception("Failed to delete stored file during import cleanup: %s", storage_path)
        raise
    return correspondence
