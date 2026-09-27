from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser


@dataclass
class ParsedAttachment:
    original_filename: str
    mime_type: str
    content: bytes


@dataclass
class ParsedEmail:
    subject: str | None
    sender: str | None
    email_date: datetime | None
    message_id: str | None
    body_text: str | None
    attachments: list[ParsedAttachment]


def parse_email(raw_email: bytes) -> ParsedEmail:
    parser = BytesParser(policy=policy.default)
    message = parser.parsebytes(raw_email)
    subject = message["Subject"]
    if subject is not None:
        subject = str(subject)
    sender = message["From"]
    if sender is not None:
        sender = str(sender)
    date_header = message["Date"]
    email_date = date_header.datetime if date_header is not None else None
    message_id = message["Message-ID"]
    if message_id is not None:
        message_id = str(message_id)
    body_part = message.get_body(preferencelist=("plain",))
    body_text = body_part.get_content() if body_part is not None else None
    attachments: list[ParsedAttachment] = []
    for index, attachment in enumerate(message.iter_attachments(), start=1):
        filename = attachment.get_filename()
        if filename is None:
            filename = f"unnamed_attachment_{index}"
        mime_type = attachment.get_content_type()
        content = attachment.get_payload(decode=True)
        if not isinstance(content, bytes):
            raise ValueError(f"Attachment '{filename}' content is not bytes")
        parsed_attachment = ParsedAttachment(filename, mime_type, content)
        attachments.append(parsed_attachment)
    return ParsedEmail(subject, sender, email_date, message_id, body_text, attachments)
