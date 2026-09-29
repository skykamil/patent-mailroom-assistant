from email.message import EmailMessage
from pathlib import Path

from app.parsers.email_parser import parse_email


def test_parse_email_reads_basic_fields():
    message = EmailMessage()
    message["Subject"] = "test"
    message["From"] = "user@test.com"
    message["Date"] = "27 Sep 2026 12:00:00 +0200"
    message["Message-ID"] = "<test-message-001@example.com>"
    message.set_content("Please see the attached documents.")
    raw_email = message.as_bytes()
    result = parse_email(raw_email)
    assert result.subject == "test"
    assert result.sender == "user@test.com"
    assert result.email_date is not None
    assert result.email_date.isoformat() == "2026-09-27T12:00:00+02:00"
    assert result.message_id == "<test-message-001@example.com>"
    assert result.body_text == "Please see the attached documents.\n"
    assert result.attachments == []


def test_parse_email_reads_attachment():
    message = EmailMessage()
    message.add_attachment(
        b"synthetic office action",
        maintype="application",
        subtype="pdf",
        filename="Office_Action.pdf",
    )
    raw_email = message.as_bytes()
    result = parse_email(raw_email)
    assert len(result.attachments) == 1
    attachment = result.attachments[0]
    assert attachment.original_filename == "Office_Action.pdf"
    assert attachment.mime_type == "application/pdf"
    assert attachment.content == b"synthetic office action"


def test_parse_email_assigns_name_to_unnamed_attachment():
    message = EmailMessage()
    message.add_attachment(
        b"unnamed content",
        maintype="application",
        subtype="octet-stream",
    )
    raw_email = message.as_bytes()
    result = parse_email(raw_email)
    assert len(result.attachments) == 1
    attachment = result.attachments[0]
    assert attachment.original_filename == "unnamed_attachment_1"
    assert attachment.mime_type == "application/octet-stream"
    assert attachment.content == b"unnamed content"


def test_parse_email_reads_multiple_attachments():
    message = EmailMessage()
    message.add_attachment(
        b"synthetic agent letter",
        maintype="application",
        subtype="pdf",
        filename="Agent_Letter.pdf"
    )
    message.add_attachment(
        b"synthetic office action",
        maintype="application",
        subtype="pdf",
        filename="Office_Action.pdf"
    )
    raw_email = message.as_bytes()
    result = parse_email(raw_email)
    assert len(result.attachments) == 2
    first_attachment = result.attachments[0]
    assert first_attachment.original_filename == "Agent_Letter.pdf"
    assert first_attachment.content == b"synthetic agent letter"
    assert first_attachment.mime_type == "application/pdf"
    second_attachment = result.attachments[1]
    assert second_attachment.original_filename == "Office_Action.pdf"
    assert second_attachment.content == b"synthetic office action"
    assert second_attachment.mime_type == "application/pdf"


def test_parse_real_eml_fixture():
    fixture_path = Path(__file__).resolve().parents[1]/"fixtures"/"emails"/"PAT-CN-001_office_action_4mo.eml"
    raw_email = fixture_path.read_bytes()
    result = parse_email(raw_email)
    assert len(result.attachments) == 2
    attachment_names = {attachment.original_filename for attachment in result.attachments}
    assert attachment_names == {"Agent_Letter.pdf", "Office_Action.pdf"}
    attachments_by_name = {attachment.original_filename: attachment for attachment in result.attachments}
    assert attachments_by_name["Agent_Letter.pdf"].mime_type == "application/pdf"
    assert attachments_by_name["Office_Action.pdf"].mime_type == "application/pdf"
    assert attachments_by_name["Agent_Letter.pdf"].content.startswith(b"%PDF")
    assert attachments_by_name["Office_Action.pdf"].content.startswith(b"%PDF")


def test_parse_email_reads_attached_email():
    inner_message = EmailMessage()
    inner_message["Subject"] = "inner message"
    inner_message["From"] = "inner@test.com"
    inner_message.set_content("Forwarded message body")
    outer_message = EmailMessage()
    outer_message["Subject"] = "outer message"
    outer_message["From"] = "outer@test.com"
    outer_message.set_content("Test message")
    outer_message.add_attachment(inner_message, filename="forwarded.eml")
    raw_email = outer_message.as_bytes()
    parsed = parse_email(raw_email)
    assert len(parsed.attachments) == 1
    assert parsed.attachments[0].original_filename == "forwarded.eml"
    assert parsed.attachments[0].mime_type == "message/rfc822"
    assert isinstance(parsed.attachments[0].content, bytes)
    assert b"Forwarded message body" in parsed.attachments[0].content
