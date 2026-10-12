from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.models.analysis import Analysis
from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.task import Task
from app.domain.analysis import AnalysisStatus, OfficeActionType
from app.domain.correspondence import ImportType
from app.domain.exceptions import CorrespondenceCaseRequiredError, OfficeActionDueDateRequiredError
from app.services import analysis_service, task_service
from tests.integration.db import TestSessionLocal


@pytest.fixture
def approval_db():
    with TestSessionLocal() as connection_session:
        connection = connection_session.connection()
        # Service commits release savepoints; the outer transaction isolates each test.
        from sqlalchemy.orm import Session
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            case = Case(internal_reference="approval-without-events", jurisdiction="PL")
            db.add(case)
            db.flush()
            correspondence = Correspondence(case_id=case.id, import_type=ImportType.EMAIL)
            db.add(correspondence)
            db.flush()
            analysis = Analysis(correspondence_id=correspondence.id)
            db.add(analysis)
            db.commit()
            yield db, correspondence, analysis
        connection_session.rollback()


@pytest.mark.parametrize("calculated", [None, date(2026, 12, 1)])
def test_office_action_approval_creates_tasks_once(approval_db, calculated):
    db, correspondence, analysis = approval_db
    analysis.office_action_type = OfficeActionType.OFFICE_ACTION_2MO
    analysis.calculated_due_date = calculated
    analysis.agent_reported_due_date = date(2026, 12, 15)
    db.commit()
    result = analysis_service.approve_analysis(db, correspondence.id)
    original_timestamp = result.approved_at
    tasks = db.scalars(select(Task).where(Task.correspondence_id == correspondence.id)).all()
    assert len(tasks) == 2
    primary = next(task for task in tasks if task.is_primary)
    review = next(task for task in tasks if not task.is_primary)
    assert primary.due_date == (calculated or date(2026, 12, 15))
    assert primary.name == OfficeActionType.OFFICE_ACTION_2MO
    assert review.due_date == result.approved_at.date() + timedelta(days=7)
    assert analysis_service.approve_analysis(db, correspondence.id).approved_at == original_timestamp
    assert len(db.scalars(select(Task).where(Task.correspondence_id == correspondence.id)).all()) == 2


def test_analysis_without_office_action_approves_without_tasks(approval_db):
    db, correspondence, analysis = approval_db
    assert analysis_service.approve_analysis(db, correspondence.id).status == AnalysisStatus.APPROVED
    assert not db.scalars(select(Task).where(Task.correspondence_id == correspondence.id)).all()


@pytest.mark.parametrize("missing_case", [True, False])
def test_missing_prerequisites_leave_analysis_pending(approval_db, missing_case):
    db, correspondence, analysis = approval_db
    analysis.office_action_type = OfficeActionType.OFFICE_ACTION
    if missing_case:
        correspondence.case_id = None
        analysis.calculated_due_date = date(2026, 12, 1)
    db.commit()
    expected = CorrespondenceCaseRequiredError if missing_case else OfficeActionDueDateRequiredError
    with pytest.raises(expected):
        analysis_service.approve_analysis(db, correspondence.id)
    assert analysis.status == AnalysisStatus.PENDING_REVIEW
    assert not db.scalars(select(Task).where(Task.correspondence_id == correspondence.id)).all()


def test_task_failure_rolls_back_approval_and_primary_task(approval_db, monkeypatch):
    db, correspondence, analysis = approval_db
    analysis.office_action_type = OfficeActionType.OFFICE_ACTION
    analysis.calculated_due_date = date(2026, 12, 1)
    db.commit()

    def fail(*args, **kwargs):
        db.flush()
        raise RuntimeError("review task failed")

    monkeypatch.setattr(task_service, "create_review_task", fail)
    with pytest.raises(RuntimeError, match="review task failed"):
        analysis_service.approve_analysis(db, correspondence.id)
    db.refresh(analysis)
    assert analysis.status == AnalysisStatus.PENDING_REVIEW
    assert analysis.approved_at is None
    assert not db.scalars(select(Task).where(Task.correspondence_id == correspondence.id)).all()


@pytest.mark.parametrize("office_action", [False, True])
def test_approval_api_returns_analysis_and_rejects_later_edits(approval_db, office_action):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_db

    db, correspondence, analysis = approval_db
    if office_action:
        analysis.office_action_type = OfficeActionType.OFFICE_ACTION
        analysis.calculated_due_date = date(2026, 12, 1)
        db.commit()
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            url = f"/correspondences/{correspondence.id}/analysis"
            response = client.post(f"{url}/approve")
            assert response.status_code == 200
            assert response.json()["status"] == "approved"
            assert response.json()["approved_at"] is not None
            assert client.post(f"{url}/approve").json() == response.json()
            assert client.put(url, json={}).status_code == 409
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_primary_task_uniqueness_uses_correspondence(approval_db):
    from sqlalchemy.exc import IntegrityError
    from app.domain.task import TaskType

    db, correspondence, _ = approval_db
    task_service.create_primary_task(db, correspondence.id, TaskType.OFFICE_ACTION, "First", date(2026, 12, 1))
    db.flush()
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            task_service.create_primary_task(db, correspondence.id, TaskType.OFFICE_ACTION, "Duplicate", date(2026, 12, 2))
            db.flush()
    task_service.create_review_task(db, correspondence.id, TaskType.OFFICE_ACTION, "Review", date(2026, 12, 1))
    db.flush()
