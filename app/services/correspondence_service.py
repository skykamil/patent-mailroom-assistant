from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence, ImportType
from app.db.models.document import Document
from app.repositories import correspondence_repository, document_repository
from app.storage import local_storage


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
            local_storage.delete_file(storage_path)
        raise
    return correspondence
