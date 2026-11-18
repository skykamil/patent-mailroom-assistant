from email.message import EmailMessage
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_prepare_review_with_single_file():
    file_id = uuid4()
    content = b"Example document content"

    response = client.post(
        "/reviews/prepare",
        files=[
            ("files", ("document.txt", content, "text/plain")),
        ],
        data={"file_ids": str(file_id)},
    )

    assert response.status_code == status.HTTP_200_OK

    files = response.json()["files"]

    assert len(files) == 1
    assert files[0]["file_id"] == str(file_id)
    assert files[0]["source_file_id"] == str(file_id)
    assert files[0]["attachment_index"] is None
    assert files[0]["filename"] == "document.txt"
    assert files[0]["mime_type"] == "text/plain"
    assert files[0]["size_bytes"] == len(content)


def test_prepare_review_with_multiple_files():
    first_id = uuid4()
    second_id = uuid4()

    response = client.post(
        "/reviews/prepare",
        files=[
            ("files", ("first.pdf", b"First PDF", "application/pdf")),
            ("files", ("second.pdf", b"Second PDF", "application/pdf")),
        ],
        data={
            "file_ids": [str(first_id), str(second_id)],
        },
    )

    assert response.status_code == status.HTTP_200_OK

    files = response.json()["files"]

    assert len(files) == 2
    assert files[0]["file_id"] == str(first_id)
    assert files[0]["filename"] == "first.pdf"
    assert files[1]["file_id"] == str(second_id)
    assert files[1]["filename"] == "second.pdf"


def test_prepare_review_rejects_mismatched_file_counts():
    response = client.post(
        "/reviews/prepare",
        files=[
            ("files", ("first.pdf", b"First", "application/pdf")),
            ("files", ("second.pdf", b"Second", "application/pdf")),
        ],
        data={"file_ids": str(uuid4())},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == (
        "Number of files and file IDs must match"
    )


def test_prepare_review_rejects_duplicate_file_ids():
    file_id = uuid4()

    response = client.post(
        "/reviews/prepare",
        files=[
            ("files", ("first.pdf", b"First", "application/pdf")),
            ("files", ("second.pdf", b"Second", "application/pdf")),
        ],
        data={
            "file_ids": [str(file_id), str(file_id)],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "File IDs must be unique"


def test_prepare_review_requires_file_ids():
    response = client.post(
        "/reviews/prepare",
        files=[
            ("files", ("document.pdf", b"Content", "application/pdf")),
        ],
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_prepare_review_rejects_invalid_email():
    response = client.post(
        "/reviews/prepare",
        files=[
            (
                "files",
                ("invalid.eml", b"This is not a valid email", "message/rfc822"),
            ),
        ],
        data={"file_ids": str(uuid4())},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "valid email" in response.json()["detail"]


def test_prepare_review_extracts_email_attachments():
    email = EmailMessage()
    email["From"] = "agent@example.com"
    email["To"] = "paralegal@example.com"
    email["Subject"] = "Office Action"

    email.set_content("Please review the attached document.")

    email.add_attachment(
        b"Example Office Action content",
        maintype="application",
        subtype="pdf",
        filename="office_action.pdf",
    )

    email_id = uuid4()

    def send_email():
        return client.post(
            "/reviews/prepare",
            files=[
                (
                    "files",
                    ("message.eml", email.as_bytes(), "message/rfc822"),
                ),
            ],
            data={"file_ids": str(email_id)},
        )

    response = send_email()

    assert response.status_code == status.HTTP_200_OK

    files = response.json()["files"]

    assert len(files) == 2

    # Original email
    assert files[0]["file_id"] == str(email_id)
    assert files[0]["filename"] == "message.eml"
    assert files[0]["attachment_index"] is None

    # Attachment
    assert files[1]["filename"] == "office_action.pdf"
    assert files[1]["source_file_id"] == str(email_id)
    assert files[1]["attachment_index"] == 0
    assert files[1]["file_id"] != str(email_id)

    # UUIDs remain stable across requests
    second_response = send_email()

    assert second_response.status_code == status.HTTP_200_OK

    second_files = second_response.json()["files"]

    assert [file["file_id"] for file in files] == [
        file["file_id"] for file in second_files
    ]
