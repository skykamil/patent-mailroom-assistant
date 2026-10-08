import pytest
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import UTC, date, datetime, timedelta
from threading import Barrier

from sqlalchemy import delete, func, select

from app.db.models.analysis import Analysis
from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.event import Event
from app.db.models.task import Task
from app.domain.analysis import AnalysisStatus, EventSelection, EventType, OfficeActionType
from app.domain.correspondence import ImportType
from app.domain.exceptions import AnalysisAlreadyApprovedError, AnalysisEventSelectionUnresolvedError, AnalysisEventTypeRequiredError, AnalysisNotFoundError, CorrespondenceCaseRequiredError, CorrespondenceNotFoundError, EventNotFoundError, EventCaseMismatchError, EventTypeMismatchError, OfficeActionDueDateRequiredError
from app.domain.task import TaskType
from app.repositories import analysis_repository, correspondence_repository, event_repository
from app.schemas.analysis import AnalysisCreate, AnalysisEventSelectionUpdate
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


def test_get_analysis_by_correspondence_id_returns_analysis():
    db = TestSessionLocal()
    correspondence = None
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
        save_result = analysis_service.save_analysis(db, correspondence.id, analysis_data)
        result = analysis_service.get_analysis_by_correspondence_id(db, correspondence.id)
        assert result.id == save_result.analysis.id
        assert result.correspondence_id == correspondence.id
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(select(Analysis).where(Analysis.correspondence_id == correspondence.id)).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_get_analysis_by_correspondence_id_raises_correspondence_not_found():
    db = TestSessionLocal()
    try:
        max_correspondence_id = db.scalar(
            select(func.max(Correspondence.id))
        ) or 0
        missing_correspondence_id = max_correspondence_id + 1

        with pytest.raises(
            CorrespondenceNotFoundError,
            match=f"Correspondence with id {missing_correspondence_id} not found",
        ):
            analysis_service.get_analysis_by_correspondence_id(db, missing_correspondence_id)
    finally:
        db.close()


def test_get_analysis_by_correspondence_id_raises_analysis_not_found():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        with pytest.raises(
            AnalysisNotFoundError,
            match=f"Analysis for correspondence with id {correspondence.id} not found",
        ):
            analysis_service.get_analysis_by_correspondence_id(db, correspondence.id)
    finally:
        db.rollback()
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_approve_analysis_sets_status_and_approved_at():
    db = TestSessionLocal()
    correspondence = None
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
        analysis_service.save_analysis(db, correspondence.id, analysis_data)
        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NO_EVENT,
            event_id=None,
        )

        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )
        result = analysis_service.approve_analysis(db, correspondence.id)
        assert result.status == AnalysisStatus.APPROVED
        assert result.approved_at is not None
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(select(Analysis).where(Analysis.correspondence_id == correspondence.id)).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_approve_analysis_does_not_change_approved_at_when_already_approved():
    db = TestSessionLocal()
    correspondence = None
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
        analysis_service.save_analysis(db, correspondence.id, analysis_data)
        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NO_EVENT,
            event_id=None,
        )

        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )
        first_result = analysis_service.approve_analysis(db, correspondence.id)
        first_approved_at = first_result.approved_at
        second_result = analysis_service.approve_analysis(db, correspondence.id)
        assert second_result.status == AnalysisStatus.APPROVED
        assert second_result.approved_at == first_approved_at
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(select(Analysis).where(Analysis.correspondence_id == correspondence.id)).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_approve_analysis_raises_analysis_not_found():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        with pytest.raises(
            AnalysisNotFoundError,
            match=f"Analysis for correspondence with id {correspondence.id} not found",
        ):
            analysis_service.approve_analysis(db, correspondence.id)
    finally:
        db.rollback()
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_save_analysis_raises_when_analysis_is_already_approved():
    db = TestSessionLocal()
    correspondence = None
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
        analysis_service.save_analysis(db, correspondence.id, analysis_data)
        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NO_EVENT,
            event_id=None,
        )

        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )
        analysis_service.approve_analysis(db, correspondence.id)
        updated_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
            agent_reported_due_date=date(2027, 2, 15),
        )
        with pytest.raises(
            AnalysisAlreadyApprovedError,
            match=f"Analysis for correspondence with id {correspondence.id} is already approved",
        ):
            analysis_service.save_analysis(db, correspondence.id, updated_analysis_data)
        analysis = analysis_service.get_analysis_by_correspondence_id(db, correspondence.id)
        assert analysis.status == AnalysisStatus.APPROVED
        assert analysis.agent_reported_due_date == date(2027, 1, 15)
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_update_analysis_event_selection_saves_unresolved():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.UNRESOLVED,
            event_id=None,
        )

        result = analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        assert result.event_selection == EventSelection.UNRESOLVED
        assert result.event_id is None
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_update_analysis_event_selection_saves_existing_event():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None
    try:
        case = Case(
            internal_reference="PAT-CN-901",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-901",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )

        result = analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        assert result.event_selection == EventSelection.EXISTING_EVENT
        assert result.event_id == event.id
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
        if event is not None:
            db.delete(event)
        if correspondence is not None:
            db.delete(correspondence)
        if case is not None:
            db.delete(case)
        db.commit()
        db.close()


def test_update_analysis_event_selection_new_event_clears_existing_event_id():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None
    try:
        case = Case(
            internal_reference="PAT-CN-902",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-902",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        existing_selection = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            existing_selection,
        )

        new_event_selection = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        result = analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            new_event_selection,
        )

        assert result.event_selection == EventSelection.NEW_EVENT
        assert result.event_id is None
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
        if event is not None:
            db.delete(event)
        if correspondence is not None:
            db.delete(correspondence)
        if case is not None:
            db.delete(case)
        db.commit()
        db.close()


def test_update_analysis_event_selection_raises_event_not_found():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        max_event_id = db.scalar(select(func.max(Event.id))) or 0
        missing_event_id = max_event_id + 1

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=missing_event_id,
        )

        with pytest.raises(EventNotFoundError):
            analysis_service.update_analysis_event_selection(
                db,
                correspondence.id,
                selection_data,
            )
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_update_analysis_event_selection_raises_event_case_mismatch():
    db = TestSessionLocal()
    first_case = None
    second_case = None
    correspondence = None
    event = None
    try:
        first_case = Case(
            internal_reference="PAT-CN-903",
            jurisdiction="CN",
        )
        second_case = Case(
            internal_reference="PAT-CN-904",
            jurisdiction="CN",
        )
        db.add_all([first_case, second_case])
        db.commit()
        db.refresh(first_case)
        db.refresh(second_case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=first_case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-903",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=second_case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )

        with pytest.raises(EventCaseMismatchError):
            analysis_service.update_analysis_event_selection(
                db,
                correspondence.id,
                selection_data,
            )
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
        if event is not None:
            db.delete(event)
        if correspondence is not None:
            db.delete(correspondence)
        if first_case is not None:
            db.delete(first_case)
        if second_case is not None:
            db.delete(second_case)
        db.commit()
        db.close()


def test_update_analysis_event_selection_raises_event_type_mismatch():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None
    try:
        case = Case(
            internal_reference="PAT-CN-905",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-905",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.PUBLICATION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )

        with pytest.raises(EventTypeMismatchError):
            analysis_service.update_analysis_event_selection(
                db,
                correspondence.id,
                selection_data,
            )
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
        if event is not None:
            db.delete(event)
        if correspondence is not None:
            db.delete(correspondence)
        if case is not None:
            db.delete(case)
        db.commit()
        db.close()


def test_update_analysis_event_selection_raises_when_analysis_is_already_approved():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )
        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NO_EVENT,
            event_id=None,
        )

        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )
        analysis_service.approve_analysis(db, correspondence.id)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )

        with pytest.raises(AnalysisAlreadyApprovedError):
            analysis_service.update_analysis_event_selection(
                db,
                correspondence.id,
                selection_data,
            )
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_save_analysis_resets_event_selection_when_event_type_changes():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None
    try:
        case = Case(
            internal_reference="PAT-CN-920",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-920",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        updated_analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-920",
            event_type=EventType.PUBLICATION,
        )
        result = analysis_service.save_analysis(
            db,
            correspondence.id,
            updated_analysis_data,
        )

        assert result.analysis.event_type == EventType.PUBLICATION
        assert result.analysis.event_selection == EventSelection.UNRESOLVED
        assert result.analysis.event_id is None
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)

        if event is not None:
            db.delete(event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_update_analysis_event_selection_waits_for_locked_correspondence():
    setup_db = TestSessionLocal()
    locking_db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        setup_db.add(correspondence)
        setup_db.commit()
        setup_db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-921",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            setup_db,
            correspondence.id,
            analysis_data,
        )

        locked_correspondence = (
            correspondence_repository.get_correspondence_by_id_for_update(
                locking_db,
                correspondence.id,
            )
        )
        assert locked_correspondence is not None

        locked_analysis = (
            analysis_repository.get_analysis_by_correspondence_id(
                locking_db,
                correspondence.id,
            )
        )
        assert locked_analysis is not None

        locked_analysis.status = AnalysisStatus.APPROVED

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )

        def update_selection():
            worker_db = TestSessionLocal()
            try:
                return analysis_service.update_analysis_event_selection(
                    worker_db,
                    correspondence.id,
                    selection_data,
                )
            finally:
                worker_db.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(update_selection)

            with pytest.raises(FutureTimeoutError):
                future.result(timeout=0.2)

            locking_db.commit()

            with pytest.raises(AnalysisAlreadyApprovedError):
                future.result(timeout=5)
    finally:
        locking_db.rollback()
        locking_db.close()

        setup_db.rollback()
        if correspondence is not None:
            analyses = setup_db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                setup_db.delete(analysis)
            setup_db.delete(correspondence)

        setup_db.commit()
        setup_db.close()


def test_approve_analysis_raises_when_event_selection_is_unresolved():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-001",
            jurisdiction="CN",
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        with pytest.raises(
            AnalysisEventSelectionUnresolvedError,
            match=(
                f"Analysis for correspondence with id {correspondence.id} "
                "has unresolved event selection"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )
        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
    finally:
        db.rollback()
        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)
            db.delete(correspondence)
        db.commit()
        db.close()


def test_approve_analysis_creates_and_links_new_event():
    db = TestSessionLocal()
    case = None
    correspondence = None
    created_event = None

    try:
        case = Case(
            internal_reference="PAT-CN-950",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-950",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=date(2027, 1, 15),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.status == AnalysisStatus.APPROVED
        assert result.event_selection == EventSelection.NEW_EVENT
        assert result.event_id is not None

        created_event = event_repository.get_event_by_id(
            db,
            result.event_id,
        )

        assert created_event is not None
        assert created_event.case_id == case.id
        assert created_event.event_type == EventType.OFFICE_ACTION
        created_task = db.scalar(
            select(Task).where(
                Task.correspondence_id == correspondence.id
            )
        )

        assert created_task is not None
        assert created_task.correspondence_id == correspondence.id
        assert created_task.event_id == result.event_id
        assert created_task.task_type == TaskType.OFFICE_ACTION
        assert created_task.name == "Office Action"
        assert created_task.due_date == date(2027, 1, 15)
        assert created_task.is_primary is True

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
            delete(Task).where(
                Task.correspondence_id == correspondence.id
                )
            )
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()

            for analysis in analyses:
                db.delete(analysis)

        if created_event is not None:
            db.delete(created_event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_new_event_does_not_create_duplicate_on_repeat():
    db = TestSessionLocal()
    case = None
    correspondence = None
    created_event = None

    try:
        case = Case(
            internal_reference="PAT-CN-951",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-951",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=date(2027, 1, 15),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        first_result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        first_event_id = first_result.event_id
        assert first_event_id is not None
        first_approved_at = first_result.approved_at

        second_result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert second_result.event_id == first_event_id
        assert second_result.approved_at == first_approved_at

        event_count = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        assert event_count == 1

        task_types = db.scalars(
            select(Task.task_type).where(
                Task.correspondence_id == correspondence.id
            )
        ).all()

        assert len(task_types) == 2
        assert task_types.count(TaskType.OFFICE_ACTION) == 1
        assert task_types.count(TaskType.REVIEW_OFFICE_ACTION) == 1

        created_event = event_repository.get_event_by_id(
            db,
            first_event_id,
        )

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Task).where(
                    Task.correspondence_id == correspondence.id
                )
            )
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()

            for analysis in analyses:
                db.delete(analysis)

        if created_event is not None:
            db.delete(created_event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_does_not_backfill_historical_approved_unresolved_analysis():
    db = TestSessionLocal()
    correspondence = None

    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis = Analysis(
            correspondence_id=correspondence.id,
            internal_reference="PAT-CN-952",
            event_selection=EventSelection.UNRESOLVED,
            status=AnalysisStatus.APPROVED,
            approved_at=datetime.now(UTC),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        original_approved_at = analysis.approved_at

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.status == AnalysisStatus.APPROVED
        assert result.approved_at == original_approved_at
        assert result.event_selection == EventSelection.UNRESOLVED
        assert result.event_id is None

    finally:
        db.rollback()

        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()

            for analysis in analyses:
                db.delete(analysis)

            db.delete(correspondence)

        db.commit()
        db.close()


def test_approve_analysis_new_event_raises_when_correspondence_has_no_case():
    db = TestSessionLocal()
    correspondence = None

    try:
        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-953",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event_count_before = db.scalar(
            select(func.count()).select_from(Event)
        )

        with pytest.raises(
            CorrespondenceCaseRequiredError,
            match=(
                f"Correspondence with id {correspondence.id} "
                "must be assigned to a case before creating a new event"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_selection == EventSelection.NEW_EVENT
        assert analysis.event_id is None

        event_count_after = db.scalar(
            select(func.count()).select_from(Event)
        )

        assert event_count_after == event_count_before

    finally:
        db.rollback()

        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()

            for analysis in analyses:
                db.delete(analysis)

            db.delete(correspondence)

        db.commit()
        db.close()


def test_approve_analysis_new_event_raises_when_event_type_is_missing():
    db = TestSessionLocal()
    case = None
    correspondence = None

    try:
        case = Case(
            internal_reference="PAT-CN-954",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-954",
            event_type=None,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event_count_before = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        with pytest.raises(
            AnalysisEventTypeRequiredError,
            match=(
                f"Analysis for correspondence with id {correspondence.id} "
                "must have an event type before creating a new event"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_selection == EventSelection.NEW_EVENT
        assert analysis.event_id is None

        event_count_after = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        assert event_count_after == event_count_before

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Event).where(
                    Event.case_id == case.id
                )
            )

        if correspondence is not None:
            db.execute(
                delete(Correspondence).where(
                    Correspondence.id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Case).where(
                    Case.id == case.id
                )
            )

        db.commit()
        db.close()


def test_approve_analysis_existing_event_uses_selected_event_without_creating_new_event():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None

    try:
        case = Case(
            internal_reference="PAT-CN-955",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-955",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event_count_before = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.status == AnalysisStatus.APPROVED
        assert result.approved_at is not None
        assert result.event_selection == EventSelection.EXISTING_EVENT
        assert result.event_id == event.id

        event_count_after = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        assert event_count_after == event_count_before
        assert event_count_after == 1

    finally:
        db.rollback()

        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)

        if event is not None:
            db.delete(event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_existing_event_revalidates_case_on_approval():
    db = TestSessionLocal()
    first_case = None
    second_case = None
    correspondence = None
    event = None

    try:
        first_case = Case(
            internal_reference="PAT-CN-956",
            jurisdiction="CN",
        )
        second_case = Case(
            internal_reference="PAT-CN-957",
            jurisdiction="CN",
        )
        db.add_all([first_case, second_case])
        db.commit()
        db.refresh(first_case)
        db.refresh(second_case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=first_case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-956",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=first_case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event.case_id = second_case.id
        db.commit()
        db.refresh(event)

        with pytest.raises(
            EventCaseMismatchError,
            match=(
                f"Event with id {event.id} "
                "does not belong to the correspondence case"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_id == event.id

    finally:
        db.rollback()

        if correspondence is not None:
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)

        if event is not None:
            db.delete(event)

        if correspondence is not None:
            db.delete(correspondence)

        if first_case is not None:
            db.delete(first_case)

        if second_case is not None:
            db.delete(second_case)

        db.commit()
        db.close()


def test_approve_analysis_new_event_rolls_back_when_commit_fails(monkeypatch):
    db = TestSessionLocal()
    case = None
    correspondence = None
    original_commit = db.commit

    try:
        case = Case(
            internal_reference="PAT-CN-959",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-959",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=date(2027, 1, 15),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event_count_before = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        def fail_commit():
            raise RuntimeError("synthetic approval commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)

        with pytest.raises(
            RuntimeError,
            match="synthetic approval commit failure",
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_selection == EventSelection.NEW_EVENT
        assert analysis.event_id is None

        event_count_after = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        assert event_count_after == event_count_before

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Event).where(
                    Event.case_id == case.id
                )
            )

        if correspondence is not None:
            db.execute(
                delete(Correspondence).where(
                    Correspondence.id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Case).where(
                    Case.id == case.id
                )
            )

        original_commit()
        db.close()


def test_approve_analysis_new_event_prevents_duplicate_on_concurrent_approval():
    db = TestSessionLocal()
    case = None
    correspondence = None

    try:
        case = Case(
            internal_reference="PAT-CN-960",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-960",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=date(2027, 1, 15),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        correspondence_id = correspondence.id
        case_id = case.id
        barrier = Barrier(2)

        def approve_in_separate_session():
            worker_db = TestSessionLocal()
            try:
                barrier.wait()

                result = analysis_service.approve_analysis(
                    worker_db,
                    correspondence_id,
                )

                return result.event_id, result.approved_at
            finally:
                worker_db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(approve_in_separate_session)
            second_future = executor.submit(approve_in_separate_session)

            first_event_id, first_approved_at = first_future.result(timeout=10)
            second_event_id, second_approved_at = second_future.result(timeout=10)

        assert first_event_id is not None
        assert second_event_id is not None
        assert first_event_id == second_event_id
        assert first_approved_at == second_approved_at

        event_count = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case_id)
        )

        assert event_count == 1

        task_types = db.scalars(
            select(Task.task_type).where(
                Task.correspondence_id == correspondence_id
            )
        ).all()

        assert len(task_types) == 2
        assert task_types.count(TaskType.OFFICE_ACTION) == 1
        assert task_types.count(TaskType.REVIEW_OFFICE_ACTION) == 1

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence_id,
        )

        assert analysis.status == AnalysisStatus.APPROVED
        assert analysis.event_id == first_event_id

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Task).where(
                    Task.correspondence_id == correspondence.id
                )
            )
            analyses = db.scalars(
                select(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            ).all()
            for analysis in analyses:
                db.delete(analysis)

        if case is not None:
            events = db.scalars(
                select(Event).where(Event.case_id == case.id)
            ).all()
            for event in events:
                db.delete(event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_existing_event_revalidates_event_type_on_approval():
    db = TestSessionLocal()
    case = None
    correspondence = None
    event = None

    try:
        case = Case(
            internal_reference="PAT-CN-958",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-958",
            event_type=EventType.OFFICE_ACTION,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.EXISTING_EVENT,
            event_id=event.id,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event.event_type = EventType.PUBLICATION
        db.commit()
        db.refresh(event)

        with pytest.raises(
            EventTypeMismatchError,
            match=(
                f"Event with id {event.id} "
                "does not match the analysis event type"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_id == event.id

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if event is not None:
            db.execute(
                delete(Event).where(
                    Event.id == event.id
                )
            )

        if correspondence is not None:
            db.execute(
                delete(Correspondence).where(
                    Correspondence.id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Case).where(
                    Case.id == case.id
                )
            )

        db.commit()
        db.close()


def test_approve_analysis_new_office_action_requires_due_date():
    db = TestSessionLocal()
    case = None
    correspondence = None

    try:
        case = Case(
            internal_reference="PAT-CN-961",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-961",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=None,
            agent_reported_due_date=None,
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        event_count_before = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        with pytest.raises(
            OfficeActionDueDateRequiredError,
            match=(
                f"Analysis for correspondence with id {correspondence.id} "
                "must have a calculated or agent-reported due date "
                "before creating a new Office Action event"
            ),
        ):
            analysis_service.approve_analysis(
                db,
                correspondence.id,
            )

        analysis = analysis_service.get_analysis_by_correspondence_id(
            db,
            correspondence.id,
        )

        assert analysis.status == AnalysisStatus.PENDING_REVIEW
        assert analysis.approved_at is None
        assert analysis.event_selection == EventSelection.NEW_EVENT
        assert analysis.event_id is None

        event_count_after = db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.case_id == case.id)
        )

        assert event_count_after == event_count_before

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Event).where(
                    Event.case_id == case.id
                )
            )

        if correspondence is not None:
            db.execute(
                delete(Correspondence).where(
                    Correspondence.id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Case).where(
                    Case.id == case.id
                )
            )

        db.commit()
        db.close()


def test_approve_analysis_new_office_action_uses_agent_reported_due_date_as_fallback():
    db = TestSessionLocal()
    case = None
    correspondence = None
    created_event = None

    try:
        case = Case(
            internal_reference="PAT-CN-962",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-962",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=None,
            agent_reported_due_date=date(2027, 2, 20),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.event_id is not None
        created_event = event_repository.get_event_by_id(
            db,
            result.event_id,
        )

        created_task = db.scalar(
            select(Task).where(
                Task.correspondence_id == correspondence.id
            )
        )

        assert created_task is not None
        assert created_task.task_type == TaskType.OFFICE_ACTION
        assert created_task.due_date == date(2027, 2, 20)
        assert created_task.is_primary is True

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Task).where(
                    Task.correspondence_id == correspondence.id
                )
            )

            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if created_event is not None:
            db.delete(created_event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_new_office_action_prefers_calculated_due_date():
    db = TestSessionLocal()
    case = None
    correspondence = None
    created_event = None

    try:
        case = Case(
            internal_reference="PAT-CN-963",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-963",
            event_type=EventType.OFFICE_ACTION,
            calculated_due_date=date(2027, 3, 10),
            agent_reported_due_date=date(2027, 3, 20),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.event_id is not None
        created_event = event_repository.get_event_by_id(
            db,
            result.event_id,
        )

        created_task = db.scalar(
            select(Task).where(
                Task.correspondence_id == correspondence.id
            )
        )

        assert created_task is not None
        assert created_task.task_type == TaskType.OFFICE_ACTION
        assert created_task.due_date == date(2027, 3, 10)
        assert created_task.is_primary is True

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Task).where(
                    Task.correspondence_id == correspondence.id
                )
            )

            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if created_event is not None:
            db.delete(created_event)

        if correspondence is not None:
            db.delete(correspondence)

        if case is not None:
            db.delete(case)

        db.commit()
        db.close()


def test_approve_analysis_new_office_action_creates_primary_and_review_tasks():
    db = TestSessionLocal()
    case = None
    correspondence = None

    try:
        case = Case(
            internal_reference="PAT-CN-965",
            jurisdiction="CN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)

        analysis_data = AnalysisCreate(
            internal_reference="PAT-CN-965",
            event_type=EventType.OFFICE_ACTION,
            office_action_type=OfficeActionType.OFFICE_ACTION_2MO,
            calculated_due_date=date(2027, 5, 12),
        )
        analysis_service.save_analysis(
            db,
            correspondence.id,
            analysis_data,
        )

        selection_data = AnalysisEventSelectionUpdate(
            event_selection=EventSelection.NEW_EVENT,
            event_id=None,
        )
        analysis_service.update_analysis_event_selection(
            db,
            correspondence.id,
            selection_data,
        )

        result = analysis_service.approve_analysis(
            db,
            correspondence.id,
        )

        assert result.status == AnalysisStatus.APPROVED
        assert result.event_id is not None
        assert result.approved_at is not None

        tasks = db.scalars(
            select(Task).where(
                Task.correspondence_id == correspondence.id
            )
        ).all()

        assert len(tasks) == 2

        primary_task = next(
            (task for task in tasks if task.is_primary),
            None,
        )
        review_task = next(
            (task for task in tasks if not task.is_primary),
            None,
        )

        assert primary_task is not None
        assert primary_task.task_type == TaskType.OFFICE_ACTION
        assert primary_task.name == "Office Action 2MO"
        assert primary_task.due_date == date(2027, 5, 12)
        assert primary_task.event_id == result.event_id
        assert primary_task.correspondence_id == correspondence.id

        assert review_task is not None
        assert review_task.task_type == TaskType.REVIEW_OFFICE_ACTION
        assert review_task.name == "Review Office Action"
        assert review_task.due_date == (
            result.approved_at.date() + timedelta(days=7)
        )
        assert review_task.event_id == result.event_id
        assert review_task.correspondence_id == correspondence.id

    finally:
        db.rollback()

        if correspondence is not None:
            db.execute(
                delete(Task).where(
                    Task.correspondence_id == correspondence.id
                )
            )
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Event).where(
                    Event.case_id == case.id
                )
            )

        if correspondence is not None:
            db.execute(
                delete(Correspondence).where(
                    Correspondence.id == correspondence.id
                )
            )

        if case is not None:
            db.execute(
                delete(Case).where(
                    Case.id == case.id
                )
            )

        db.commit()
        db.close()
