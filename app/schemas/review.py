from uuid import UUID
from pydantic import BaseModel

class ReviewFileRead(BaseModel):
    file_id: UUID
    source_file_id: UUID
    attachment_index: int | None = None
    filename: str
    mime_type: str
    size_bytes: int


class ReviewPrepareResponse(BaseModel):
    files: list[ReviewFileRead]
