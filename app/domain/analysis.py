from enum import StrEnum


class EventType(StrEnum):
    OFFICE_ACTION = "office_action"
    APPLICATION = "application"
    PUBLICATION = "publication"


class OfficeActionType(StrEnum):
    OFFICE_ACTION = "Office Action"
    OFFICE_ACTION_1MO = "Office Action 1MO"
    OFFICE_ACTION_2MO = "Office Action 2MO"
    OFFICE_ACTION_3MO = "Office Action 3MO"
    OFFICE_ACTION_4MO = "Office Action 4MO"


class AnalysisStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
