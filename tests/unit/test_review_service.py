from email.message import EmailMessage
from uuid import uuid4, uuid5

import pytest

from app.domain.doc_type import DocType
from app.domain.exceptions import InvalidFileSelectionError
from app.services.review_service import (
    ExpandedDocument,
    FileSelection,
    IncomingDocument,
    expand_incoming_documents,
    prepare_incoming_documents,
    select_documents_to_save,
)


def test_prepare_incoming_documents():
    first_id = uuid4()
    second_id = uuid4()

    documents = [
        IncomingDocument(
            file_id=first_id,
            original_filename="office_action.pdf",
            content=b"Example PDF content",
            mime_type="application/pdf",
        ),
        IncomingDocument(
            file_id=second_id,
            original_filename="claims.docx",
            content=b"Example DOCX content",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ]

    result = prepare_incoming_documents(documents)

    assert len(result) == 2

    assert result[0].file_id == first_id
    assert result[0].source_file_id == first_id
    assert result[0].attachment_index is None
    assert result[0].filename == "office_action.pdf"
    assert result[0].mime_type == "application/pdf"
    assert result[0].size_bytes == len(documents[0].content)

    assert result[1].file_id == second_id
    assert result[1].source_file_id == second_id
    assert result[1].attachment_index is None
    assert result[1].filename == "claims.docx"
    assert result[1].mime_type == documents[1].mime_type
    assert result[1].size_bytes == len(documents[1].content)



def test_prepare_incoming_documents_extracts_email_attachments():
    email = EmailMessage()
    email["From"] = "agent@example.com"
    email["To"] = "paralegal@example.com"
    email["Subject"] = "Office Action"

    email.set_content("Please find the attached documents.")

    email.add_attachment(
        b"Example PDF content",
        maintype="application",
        subtype="pdf",
        filename="office_action.pdf",
    )

    email.add_attachment(
        b"Example DOCX content",
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="claims.docx",
    )

    email_id = uuid4()

    document = IncomingDocument(
        file_id=email_id,
        original_filename="message.EML",
        content=email.as_bytes(),
        mime_type="message/rfc822",
    )

    result = prepare_incoming_documents([document])

    # Original email + two attachments
    assert len(result) == 3

    # Original email comes first
    assert result[0].filename == "message.EML"
    assert result[0].file_id == email_id
    assert result[0].source_file_id == email_id
    assert result[0].attachment_index is None

    # Attachments
    assert result[1].filename == "office_action.pdf"
    assert result[1].attachment_index == 0
    assert result[1].source_file_id == email_id

    assert result[2].filename == "claims.docx"
    assert result[2].attachment_index == 1
    assert result[2].source_file_id == email_id

    # All files have unique UUIDs
    assert len({file.file_id for file in result}) == 3

    # Reprocessing preserves UUIDs
    second_result = prepare_incoming_documents([document])

    assert [file.file_id for file in result] == [
        file.file_id for file in second_result
    ]


def test_expand_incoming_documents_keeps_regular_file_content():
    file_id = uuid4()
    content = b"Example PDF content"

    result = expand_incoming_documents(
        [
            IncomingDocument(
                file_id=file_id,
                original_filename="office_action.pdf",
                content=content,
                mime_type="application/pdf",
            )
        ]
    )

    assert len(result) == 1
    assert result[0].file_id == file_id
    assert result[0].source_file_id == file_id
    assert result[0].attachment_index is None
    assert result[0].filename == "office_action.pdf"
    assert result[0].content == content


def test_expand_incoming_documents_returns_email_attachment_content():
    email = EmailMessage()
    email["From"] = "agent@example.com"
    email["To"] = "paralegal@example.com"
    email["Subject"] = "Office Action"
    email.set_content("Please find the attached documents.")
    email.add_attachment(
        b"Example PDF content",
        maintype="application",
        subtype="pdf",
        filename="office_action.pdf",
    )
    email.add_attachment(
        b"Example DOCX content",
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="claims.docx",
    )
    email_id = uuid4()
    email_content = email.as_bytes()

    result = expand_incoming_documents(
        [
            IncomingDocument(
                file_id=email_id,
                original_filename="message.eml",
                content=email_content,
                mime_type="message/rfc822",
            )
        ]
    )

    assert len(result) == 3

    assert result[0].file_id == email_id
    assert result[0].content == email_content

    assert result[1].file_id == uuid5(email_id, "0")
    assert result[1].source_file_id == email_id
    assert result[1].attachment_index == 0
    assert result[1].content == b"Example PDF content"

    assert result[2].file_id == uuid5(email_id, "1")
    assert result[2].source_file_id == email_id
    assert result[2].attachment_index == 1
    assert result[2].content == b"Example DOCX content"


def test_expand_incoming_documents_requires_at_least_one_document():
    with pytest.raises(ValueError):
        expand_incoming_documents([])


def make_expanded_document(file_id, filename="file.pdf"):
    return ExpandedDocument(
        file_id=file_id,
        source_file_id=file_id,
        attachment_index=None,
        filename=filename,
        mime_type="application/pdf",
        content=b"content",
    )


def test_select_documents_to_save_keeps_expanded_order_and_skips_unselected():
    first_id, second_id, third_id = uuid4(), uuid4(), uuid4()
    expanded_documents = [
        make_expanded_document(first_id),
        make_expanded_document(second_id),
        make_expanded_document(third_id),
    ]
    selections = [
        FileSelection(file_id=third_id, doc_type=DocType.CLAIMS),
        FileSelection(file_id=first_id, doc_type=DocType.OFFICE_ACTION),
    ]

    result = select_documents_to_save(expanded_documents, selections)

    assert [item.document.file_id for item in result] == [first_id, third_id]
    assert [item.doc_type for item in result] == [DocType.OFFICE_ACTION, DocType.CLAIMS]


def test_select_documents_to_save_requires_selection():
    expanded_documents = [make_expanded_document(uuid4())]

    with pytest.raises(InvalidFileSelectionError, match="No files selected"):
        select_documents_to_save(expanded_documents, [])


def test_select_documents_to_save_rejects_duplicate_file_ids():
    file_id = uuid4()
    expanded_documents = [make_expanded_document(file_id)]
    selections = [
        FileSelection(file_id=file_id, doc_type=DocType.OTHER),
        FileSelection(file_id=file_id, doc_type=DocType.CLAIMS),
    ]

    with pytest.raises(InvalidFileSelectionError, match="Duplicate file IDs"):
        select_documents_to_save(expanded_documents, selections)


def test_select_documents_to_save_rejects_unknown_file_id():
    known_id, unknown_id = uuid4(), uuid4()
    expanded_documents = [make_expanded_document(known_id)]
    selections = [
        FileSelection(file_id=known_id, doc_type=DocType.OTHER),
        FileSelection(file_id=unknown_id, doc_type=DocType.OTHER),
    ]

    with pytest.raises(InvalidFileSelectionError, match=str(unknown_id)):
        select_documents_to_save(expanded_documents, selections)
