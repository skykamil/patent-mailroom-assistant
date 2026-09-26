from pydantic import BaseModel, Field

class DocumentUploadMetadata(BaseModel):
    original_filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
