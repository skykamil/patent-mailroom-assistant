import pytest

from app.domain.exceptions import ApplicationNumberAlreadyExistsError, CaseAlreadyExistsError
from app.schemas.case import CaseCreate
from app.services import case_service
from tests.integration.db import TestSessionLocal, delete_case_by_internal_reference

def test_create_case_raises_application_number_already_exists_error_for_duplicate_application_number_in_same_jurisdiction():
    db = TestSessionLocal()
    delete_case_by_internal_reference("PAT-CN-905")
    delete_case_by_internal_reference("PAT-CN-906")
    try:
        first_case_data = CaseCreate(
            internal_reference="PAT-CN-905",
            application_number="123456789",
        )
        case_service.create_case(db, first_case_data)
        second_case_data = CaseCreate(
            internal_reference="PAT-CN-906",
            application_number="123456789",
        )
        with pytest.raises(ApplicationNumberAlreadyExistsError):
            case_service.create_case(db, second_case_data)
    finally:
        db.close()
        delete_case_by_internal_reference("PAT-CN-905")
        delete_case_by_internal_reference("PAT-CN-906")

def test_duplicate_internal_reference_conflict_at_database_write(monkeypatch):
    monkeypatch.setattr(
        case_service.case_repository,
        "get_case_by_internal_reference",
        lambda db, internal_reference: None
    )
    db = TestSessionLocal()
    delete_case_by_internal_reference("PAT-CN-909")
    try:
        first_case_data = CaseCreate(
            internal_reference="PAT-CN-909"
        )
        case_service.create_case(db, first_case_data)
        second_case_data = CaseCreate(
            internal_reference="PAT-CN-909"
        )
        with pytest.raises(CaseAlreadyExistsError):
            case_service.create_case(db, second_case_data)
    finally:
        db.close()
        delete_case_by_internal_reference("PAT-CN-909")
