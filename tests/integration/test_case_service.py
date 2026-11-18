import pytest

from app.domain.exceptions import CaseAlreadyExistsError, CaseReferenceNotFoundError
from app.schemas.case import CaseCreate
from app.services import case_service
from tests.integration.db import TestSessionLocal, delete_case_by_internal_reference


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


def test_get_case_by_reference_ignores_case_and_surrounding_spaces():
    db = TestSessionLocal()
    delete_case_by_internal_reference("PAT-CN-920")

    try:
        created_case = case_service.create_case(
            db, CaseCreate(internal_reference="PAT-CN-920")
        )

        found_case = case_service.get_case_by_reference(db, "  pat-cn-920 ")

        assert found_case.id == created_case.id
        assert found_case.internal_reference == "PAT-CN-920"

    finally:
        db.close()
        delete_case_by_internal_reference("PAT-CN-920")


def test_get_case_by_reference_raises_when_reference_does_not_exist():
    db = TestSessionLocal()
    delete_case_by_internal_reference("PAT-CN-921")

    try:
        with pytest.raises(CaseReferenceNotFoundError, match="PAT-CN-921"):
            case_service.get_case_by_reference(db, " pat-cn-921 ")

    finally:
        db.close()
