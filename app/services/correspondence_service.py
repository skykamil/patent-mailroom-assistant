import logging
from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence
from app.db.models.document import Document
from app.domain.correspondence import ImportType
from app.parsers.email_parser import parse_email
from app.repositories import correspondence_repository, document_repository
from app.services import case_service
from app.storage import local_storage


logger = logging.getLogger(__name__)


@dataclass
class IncomingDocument:
    original_filename: str
    content: bytes
    mime_type: str


@dataclass
class EmailImportResult:
    correspondence: Correspondence
    created: bool


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


def import_email(
    db: Session,
    raw_email: bytes,
    original_filename: str,
    case_id: int | None = None,
) -> EmailImportResult:
    if case_id is not None:
        case_service.get_case_by_id(db, case_id)
    source_sha256 = sha256(raw_email).hexdigest()
    existing_correspondence = correspondence_repository.get_correspondence_by_source_sha256(db, source_sha256)
    if existing_correspondence is not None:
        return EmailImportResult(correspondence=existing_correspondence, created=False)
    saved_paths: list[str] = []
    parsed_email = parse_email(raw_email)
    try:
        stored_email = local_storage.save_file(content=raw_email, original_filename=original_filename)
        saved_paths.append(stored_email.storage_path)
        correspondence = Correspondence(
            case_id=case_id,
            import_type=ImportType.EMAIL,
            source_sha256=source_sha256,
            source_storage_path=stored_email.storage_path,
            email_subject=parsed_email.subject,
            email_sender=parsed_email.sender,
            email_date=parsed_email.email_date,
            email_message_id=parsed_email.message_id,
            body_text=parsed_email.body_text,
        )
        db.add(correspondence)
        db.flush()
        correspondence_id = correspondence.id
        for attachment in parsed_email.attachments:
            stored_attachment = local_storage.save_file(
                content=attachment.content,
                original_filename=attachment.original_filename,
            )
            saved_paths.append(stored_attachment.storage_path)
            document = Document(
                correspondence_id=correspondence_id,
                original_filename=attachment.original_filename,
                storage_path=stored_attachment.storage_path,
                mime_type=attachment.mime_type,
                file_size=stored_attachment.file_size,
                sha256=stored_attachment.sha256,
            )
            db.add(document)
        db.commit()
        return EmailImportResult(
            correspondence=correspondence,
            created=True,
        )
    except Exception:
        db.rollback()
        for storage_path in saved_paths:
            try:
                local_storage.delete_file(storage_path)
            except OSError:
                logger.exception("Failed to delete stored file during import cleanup: %s", storage_path)
        raise
