from dataclasses import dataclass
from uuid import UUID, uuid5

from app.schemas.review import ReviewFileRead
from app.parsers.email_parser import parse_email


@dataclass
class IncomingDocument:
    file_id: UUID
    original_filename: str
    content: bytes
    mime_type: str


def prepare_incoming_documents(documents: list[IncomingDocument]) -> list[ReviewFileRead] :
    prepared_documents = []
    if not documents:
        raise ValueError("At least one document is required")
    for document in documents:
        file_id = document.file_id
        source_file_id = file_id
        attachment_index = None
        filename = document.original_filename
        mime_type = document.mime_type
        size_bytes = len(document.content)
        prepared_documents.append(ReviewFileRead(file_id=file_id, source_file_id=source_file_id, attachment_index=attachment_index, filename=filename, mime_type=mime_type, size_bytes=size_bytes))
        if document.original_filename.lower().endswith(".eml"):
            parsed_email = parse_email(document.content)
            for attachment_index, attachment in enumerate(parsed_email.attachments, start=0):
                attachment_file_id = uuid5(document.file_id, str(attachment_index))
                attachment_filename = attachment.original_filename
                attachment_mime_type = attachment.mime_type
                attachment_size_bytes = len(attachment.content)
                prepared_documents.append(ReviewFileRead(file_id=attachment_file_id, source_file_id=document.file_id, attachment_index=attachment_index, filename=attachment_filename, mime_type=attachment_mime_type, size_bytes=attachment_size_bytes))
    return prepared_documents
