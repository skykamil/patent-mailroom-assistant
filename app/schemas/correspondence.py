from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.correspondence import ImportType


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    mime_type: str
    file_size: int
    sha256: str


class CorrespondenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_id: int | None
    import_type: ImportType
    imported_at: datetime
    documents: list[DocumentRead]
