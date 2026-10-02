import pytest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from sqlalchemy import func, select

from app.db.models.analysis import Analysis
from app.db.models.correspondence import Correspondence
from app.domain.analysis import EventType, OfficeActionType
from app.domain.correspondence import ImportType
from app.domain.exceptions import CorrespondenceNotFoundError
from app.schemas.analysis import AnalysisCreate
from app.services import analysis_service
from tests.integration.db import TestSessionLocal


def test_save_analysis_creates_analysis_for_existing_correspondence():
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
        result = analysis_service.save_analysis(db, correspondence.id, analysis_data)
        analysis = result.analysis
        assert analysis.id is not None
        assert analysis.correspondence_id == correspondence.id
        assert analysis.internal_reference == "PAT-CN-001"
        assert analysis.jurisdiction == "CN"
        assert analysis.application_number == "202611111111.1"
        assert analysis.event_type == EventType.OFFICE_ACTION
        assert analysis.office_action_type == OfficeActionType.OFFICE_ACTION_4MO
        assert (analysis.document_date,
                analysis.agent_notification_date,
                analysis.agent_reported_due_date,
                analysis.calculated_due_date,
        ) == (
            analysis_data.document_date,
            analysis_data.agent_notification_date,
            analysis_data.agent_reported_due_date,
            analysis_data.calculated_due_date,
        )
        assert analysis.created_at is not None
        assert analysis.updated_at is None
        assert result.created is True
    finally:
        db.rollback()
        if result is not None:
            db.delete(result.analysis)
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_save_analysis_updates_existing_analysis():
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
        first_result = analysis_service.save_analysis(db, correspondence.id, analysis_data)
        first_analysis = first_result.analysis
        first_result_id = first_analysis.id
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
        assert first_result.created is True
        second_result = analysis_service.save_analysis(db, correspondence.id, updated_analysis_data)
        second_analysis = second_result.analysis
        assert second_result.created is False
        assert second_analysis.id == first_result_id
        assert second_analysis.agent_reported_due_date is None
        assert second_analysis.updated_at is not None
        analysis_count = db.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.correspondence_id == correspondence.id)
        )
        assert analysis_count == 1
    finally:
        db.rollback()
        if first_result is not None:
            db.delete(first_result.analysis)
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_save_analysis_raises_correspondence_not_found():
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
            analysis_service.save_analysis(db, missing_correspondence_id, analysis_data)
    finally:
        db.close()


def test_save_analysis_rolls_back_when_create_commit_fails(monkeypatch):
    db = TestSessionLocal()
    correspondence = None
    original_commit = db.commit
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
        )

        def fail_commit():
            raise RuntimeError("synthetic commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            analysis_service.save_analysis(db, correspondence.id, analysis_data)
        analysis_count = db.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.correspondence_id == correspondence.id)
        )
        assert analysis_count == 0
    finally:
        db.rollback()
        if correspondence is not None:
            db.delete(correspondence)
        original_commit()
        db.close()


def test_save_analysis_rolls_back_when_update_commit_fails(monkeypatch):
    db = TestSessionLocal()
    correspondence = None
    first_result = None
    original_commit = db.commit
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            agent_reported_due_date=date(2027, 1, 15),
        )
        first_result = analysis_service.save_analysis(db, correspondence.id, analysis_data)
        updated_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            agent_reported_due_date=None,
        )

        def fail_commit():
            db.flush()
            raise RuntimeError("synthetic commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            analysis_service.save_analysis(db, correspondence.id, updated_analysis_data)
        db.refresh(first_result.analysis)
        assert first_result.analysis.agent_reported_due_date == date(2027, 1, 15)
        assert first_result.analysis.updated_at is None
    finally:
        db.rollback()
        if first_result is not None:
            db.delete(first_result.analysis)
        if correspondence is not None:
            db.delete(correspondence)
        original_commit()
        db.close()


def test_save_analysis_prevents_duplicate_on_concurrent_first_save():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        correspondence_id = correspondence.id
        first_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            agent_reported_due_date=date(2027, 1, 15),
        )
        second_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            agent_reported_due_date=None,
        )
        barrier = Barrier(2)

        def save_in_separate_session(analysis_data: AnalysisCreate) -> int:
            worker_db = TestSessionLocal()
            try:
                barrier.wait()
                result = analysis_service.save_analysis(worker_db, correspondence_id, analysis_data)
                return result.analysis.id
            finally:
                worker_db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(save_in_separate_session, first_analysis_data)
            second_future = executor.submit(save_in_separate_session, second_analysis_data)
            first_analysis_id = first_future.result(timeout=10)
            second_analysis_id = second_future.result(timeout=10)
        analysis_count = db.scalar(
            select(func.count())
            .select_from(Analysis)
            .where(Analysis.correspondence_id == correspondence_id)
        )
        assert first_analysis_id == second_analysis_id
        assert analysis_count == 1
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(select(Analysis).where(Analysis.correspondence_id == correspondence.id)).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()
