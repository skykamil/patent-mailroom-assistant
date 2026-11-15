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


@dataclass
class ExpandedDocument:
    file_id: UUID
    source_file_id: UUID
    attachment_index: int | None
    filename: str
    mime_type: str
    content: bytes


def expand_incoming_documents(documents: list[IncomingDocument]) -> list[ExpandedDocument]:
    expanded_documents = []
    if not documents:
        raise ValueError("At least one document is required")
    for document in documents:
        file_id = document.file_id
        source_file_id = file_id
        attachment_index = None
        filename = document.original_filename
        mime_type = document.mime_type
        content = document.content
        expanded_documents.append(ExpandedDocument(file_id=file_id, source_file_id=source_file_id, attachment_index=attachment_index, filename=filename, mime_type=mime_type, content=content))
        if document.original_filename.lower().endswith(".eml"):
            parsed_email = parse_email(document.content)
            for attachment_index, attachment in enumerate(parsed_email.attachments, start=0):
                attachment_file_id = uuid5(document.file_id, str(attachment_index))
                attachment_filename = attachment.original_filename
                attachment_mime_type = attachment.mime_type
                attachment_content = attachment.content
                expanded_documents.append(ExpandedDocument(file_id=attachment_file_id, source_file_id=document.file_id, attachment_index=attachment_index, filename=attachment_filename, mime_type=attachment_mime_type, content=attachment_content))
    return expanded_documents


def prepare_incoming_documents(documents: list[IncomingDocument]) -> list[ReviewFileRead]:
    prepared_documents = []
    expanded_documents = expand_incoming_documents(documents)
    for document in expanded_documents:
        file_id = document.file_id
        source_file_id = document.source_file_id
        attachment_index = document.attachment_index
        filename = document.filename
        mime_type = document.mime_type
        size_bytes = len(document.content)
        prepared_documents.append(ReviewFileRead(file_id=file_id, source_file_id=source_file_id, attachment_index=attachment_index, filename=filename, mime_type=mime_type, size_bytes=size_bytes))
    return prepared_documents
