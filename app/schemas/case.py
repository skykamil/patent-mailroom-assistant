from datetime import date

from pydantic import BaseModel

class CaseCreate(BaseModel):
    internal_reference: str
    application_number: str | None = None
    application_date: date | None = None
    publication_number: str | None = None
    publication_date: date | None = None
    grant_number: str | None = None
    grant_date: date | None = None
    agent_reference: str | None = None
