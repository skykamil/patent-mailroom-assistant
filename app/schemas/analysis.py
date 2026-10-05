from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.analysis import AnalysisStatus, EventSelection, EventType, OfficeActionType


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    internal_reference: str | None = Field(default=None, max_length=50)
    jurisdiction: str | None = Field(default=None, max_length=2)
    application_number: str | None = Field(default=None, max_length=50)
    event_type: EventType | None = None
    office_action_type: OfficeActionType | None = None
    document_date: date | None = None
    agent_notification_date: date | None = None
    agent_reported_due_date: date | None = None
    calculated_due_date: date | None = None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    correspondence_id: int
    event_id: int | None = None
    event_selection: EventSelection
    internal_reference: str | None = None
    jurisdiction: str | None = None
    application_number: str | None = None
    event_type: EventType | None = None
    office_action_type: OfficeActionType | None = None
    document_date: date | None = None
    agent_notification_date: date | None = None
    agent_reported_due_date: date | None = None
    calculated_due_date: date | None = None
    created_at: datetime
    updated_at: datetime | None = None
    status: AnalysisStatus
    approved_at: datetime | None = None


class AnalysisEventSelectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_selection: EventSelection
    event_id: int | None = None

    @model_validator(mode="after")
    def validate_event_selection_and_id(self) -> Self:
        if self.event_selection == EventSelection.UNRESOLVED:
            if self.event_id is not None:
                raise ValueError("event_id must be None when event_selection is unresolved")
        if self.event_selection == EventSelection.NEW_EVENT:
            if self.event_id is not None:
                raise ValueError("event_id must be None when event_selection is new_event")
        if self.event_selection == EventSelection.EXISTING_EVENT:
            if self.event_id is None:
                raise ValueError("event_id is required when event_selection is existing_event")
        return self
