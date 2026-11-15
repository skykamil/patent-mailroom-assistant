from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.case import Case
from app.db.models.task import Task
from app.domain.task import TaskType
from tests.integration.db import TestSessionLocal


def test_task_belongs_to_case():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"TEST-{uuid4().hex[:12]}")
        task = Task(
            case=case,
            submission_id=str(uuid4()),
            task_type=TaskType.OFFICE_ACTION_3MO,
            start_date=date(2026, 10, 15),
            due_date=date(2027, 1, 15),
            dates_manually_adjusted=False,
        )

        db.add(task)
        db.flush()

        assert task.id is not None
        assert task.case_id == case.id
        assert task.case is case
        assert task in case.tasks

    finally:
        db.rollback()
        db.close()


def test_task_requires_submission_id():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"TEST-{uuid4().hex[:12]}")
        task = Task(
            case=case,
            task_type=TaskType.OFFICE_ACTION,
            start_date=date(2026, 10, 15),
            due_date=date(2027, 1, 15),
            dates_manually_adjusted=False,
        )

        db.add(task)

        with pytest.raises(IntegrityError):
            db.flush()

    finally:
        db.rollback()
        db.close()
