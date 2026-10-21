from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.domain.analysis import AnalysisStatus, OfficeActionType


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    correspondence_id: int
    internal_reference: str | None = None
    jurisdiction: str | None = None
    application_number: str | None = None
    office_action_type: OfficeActionType | None = None
    document_date: date | None = None
    agent_notification_date: date | None = None
    agent_reported_due_date: date | None = None
    calculated_due_date: date | None = None
    created_at: datetime
    updated_at: datetime | None = None
    status: AnalysisStatus
    approved_at: datetime | None = None
