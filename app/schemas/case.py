from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.case_rules import validate_internal_reference_format

class CaseCreate(BaseModel):
    internal_reference: str = Field(max_length=50)

    @field_validator("internal_reference")
    @classmethod
    def validate_internal_reference(cls, value: str) -> str:
        validate_internal_reference_format(value)
        return value
    
    application_number: str | None = Field(default=None, max_length=50)
    application_date: date | None = None
    publication_number: str | None = Field(default=None, max_length=50)
    publication_date: date | None = None
    grant_number: str | None = Field(default=None, max_length=50)
    grant_date: date | None = None
    agent_reference: str | None = Field(default=None, max_length=50)

class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    internal_reference: str
    jurisdiction: str
    application_number: str | None = None
    application_date: date | None = None
    publication_number: str | None = None
    publication_date: date | None = None
    grant_number: str | None = None
    grant_date: date | None = None
    agent_reference: str | None = None

class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_number: str | None = Field(default=None, max_length=50)
    application_date: date | None = None
    publication_number: str | None = Field(default=None, max_length=50)
    publication_date: date | None = None
    grant_number: str | None = Field(default=None, max_length=50)
    grant_date: date | None = None
    agent_reference: str | None = Field(default=None, max_length=50)
