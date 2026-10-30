from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    correspondence_id: int
    proposed_tasks: list[dict]
    review_decisions: dict
    created_at: datetime
