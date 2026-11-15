from enum import StrEnum


class DocType(StrEnum):
    OFFICE_ACTION = "office_action"
    AGENT_LETTER = "agent_letter"
    SEARCH_REPORT = "search_report"
    CLAIMS = "claims"
    SPECIFICATION = "specification"
    SUBMISSION = "submission"
    INVOICE = "invoice"
    OFFICIAL_LETTER = "official_letter"
    REFERENCE = "reference"
    OTHER = "other"
    EML_COMMUNICATION_AGENT = "eml_communication_agent"
    EML_REVIEW_COMMUNICATION_AGENT = "eml_review_communication_agent"
    EML_REVIEW_OFFICE_ACTION = "eml_review_office_action"
    EML_REMINDER = "eml_reminder"
