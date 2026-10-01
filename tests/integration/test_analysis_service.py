import pytest
from datetime import date

from sqlalchemy import func, select

from app.db.models.analysis import Analysis
from app.db.models.correspondence import Correspondence
from app.domain.analysis import EventType, OfficeActionType
from app.domain.correspondence import ImportType
from app.domain.exceptions import CorrespondenceNotFoundError
from app.schemas.analysis import AnalysisCreate
from app.services import analysis_service
from tests.integration.db import TestSessionLocal


def test_create_analysis_creates_analysis_for_existing_correspondence():
    db = TestSessionLocal()
    correspondence = None
    result = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            application_number="202611111111.1",
            event_type=EventType.OFFICE_ACTION,
            office_action_type=OfficeActionType.OFFICE_ACTION_4MO,
            document_date=date(2026, 9, 15),
            agent_notification_date=date(2026, 9, 18),
            agent_reported_due_date=date(2027, 1, 15),
            calculated_due_date=date(2027, 1, 15)
        )
        result = analysis_service.create_analysis(db, correspondence.id, analysis_data)
        assert result.id is not None
        assert result.correspondence_id == correspondence.id
        assert result.internal_reference == "PAT-CN-001"
        assert result.jurisdiction == "CN"
        assert result.application_number == "202611111111.1"
        assert result.event_type == EventType.OFFICE_ACTION
        assert result.office_action_type == OfficeActionType.OFFICE_ACTION_4MO
        assert (result.document_date,
                result.agent_notification_date,
                result.agent_reported_due_date,
                result.calculated_due_date,
        ) == (
            analysis_data.document_date,
            analysis_data.agent_notification_date,
            analysis_data.agent_reported_due_date,
            analysis_data.calculated_due_date,
        )
        assert result.created_at is not None
        assert result.updated_at is None
    finally:
        db.rollback()
        if result is not None:
            db.delete(result)
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_create_analysis_updates_existing_analysis():
    db = TestSessionLocal()
    correspondence = None
    first_result = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            application_number="202611111111.1",
            event_type=EventType.OFFICE_ACTION,
            office_action_type=OfficeActionType.OFFICE_ACTION_4MO,
            document_date=date(2026, 9, 15),
            agent_notification_date=date(2026, 9, 18),
            agent_reported_due_date=date(2027, 1, 15),
            calculated_due_date=date(2027, 1, 15)
        )
        first_result = analysis_service.create_analysis(db, correspondence.id, analysis_data)
        first_result_id = first_result.id
        updated_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            application_number="202611111111.1",
            event_type=EventType.OFFICE_ACTION,
            office_action_type=OfficeActionType.OFFICE_ACTION_4MO,
            document_date=date(2026, 9, 15),
            agent_notification_date=date(2026, 9, 18),
            agent_reported_due_date=None,
            calculated_due_date=date(2027, 1, 15)
        )
        second_result = analysis_service.create_analysis(db, correspondence.id, updated_analysis_data)
        assert second_result.id == first_result_id
        assert second_result.agent_reported_due_date is None
        assert second_result.updated_at is not None
        analysis_count = db.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.correspondence_id == correspondence.id)
        )
        assert analysis_count == 1
    finally:
        db.rollback()
        if first_result is not None:
            db.delete(first_result)
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_create_analysis_raises_correspondence_not_found():
    db = TestSessionLocal()
    try:
        max_correspondence_id = db.scalar(select(func.max(Correspondence.id))) or 0
        missing_correspondence_id = max_correspondence_id + 1
        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            application_number="202611111111.1",
        )
        with pytest.raises(CorrespondenceNotFoundError):
            analysis_service.create_analysis(db, missing_correspondence_id, analysis_data)
    finally:
        db.close()
