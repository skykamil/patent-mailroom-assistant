from dataclasses import dataclass
from uuid import UUID, uuid5

from app.domain.doc_type import DocType
from app.domain.exceptions import InvalidFileSelectionError
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


@dataclass
class FileSelection:
    file_id: UUID
    doc_type: DocType


@dataclass
class SelectedDocument:
    document: ExpandedDocument
    doc_type: DocType


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


def select_documents_to_save(expanded_documents: list[ExpandedDocument], selections: list[FileSelection]) -> list[SelectedDocument]:
    selected_documents = []
    if not selections:
        raise InvalidFileSelectionError("No files selected")
    selected_file_ids = []
    for selection in selections:
        selected_file_ids.append(selection.file_id)
    if len(set(selected_file_ids)) != len(selections):
        raise InvalidFileSelectionError("Duplicate file IDs in selection")
    doc_type_by_file_id = {}
    for selection in selections:
        doc_type_by_file_id[selection.file_id] = selection.doc_type
    known_file_ids = set()
    for document in expanded_documents:
        known_file_ids.add(document.file_id)
    unknown_file_ids = set(selected_file_ids) - known_file_ids
    if unknown_file_ids:
        unknown_ids_text = ", ".join(str(file_id) for file_id in unknown_file_ids)
        raise InvalidFileSelectionError(f"File IDs not found in uploaded files: {unknown_ids_text}")
    for document in expanded_documents:
        if document.file_id in doc_type_by_file_id:
            selected_documents.append(SelectedDocument(document=document, doc_type=doc_type_by_file_id[document.file_id]))
    return selected_documents
