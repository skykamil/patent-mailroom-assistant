from dataclasses import dataclass


@dataclass
class IncomingDocument:
    original_filename: str
    content: bytes
    mime_type: str
