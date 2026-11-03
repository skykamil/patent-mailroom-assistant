from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.task import Task
from app.domain.task import TaskType
from tests.integration.db import TestSessionLocal


def test_task_belongs_to_correspondence():
    db = TestSessionLocal()

    try:
        case = Case(internal_reference=f"TEST-{uuid4().hex[:12]}")
        correspondence = Correspondence(
            case=case,
            submission_id=str(uuid4()),
        )
        task = Task(
            case=case,
            correspondence=correspondence,
            task_type=TaskType.OFFICE_ACTION_3MO,
            start_date=date(2026, 10, 15),
            due_date=date(2027, 1, 15),
            dates_manually_adjusted=False,
        )

        db.add(task)
        db.flush()

        assert task.id is not None
        assert task.case_id == case.id
        assert task.correspondence_id == correspondence.id
        assert task.correspondence is correspondence
        assert task in correspondence.tasks

    finally:
        db.rollback()
        db.close()


def test_task_requires_correspondence():
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


def test_task_rejects_correspondence_from_different_case():
    db = TestSessionLocal()

    try:
        case_a = Case(internal_reference=f"TEST-{uuid4().hex[:12]}")
        case_b = Case(internal_reference=f"TEST-{uuid4().hex[:12]}")

        correspondence = Correspondence(
            case=case_a,
            submission_id=str(uuid4()),
        )

        db.add_all([case_a, case_b, correspondence])
        db.flush()

        task = Task(
            case=case_b,
            correspondence=correspondence,
            task_type=TaskType.OFFICE_ACTION_2MO,
            start_date=date(2026, 10, 15),
            due_date=date(2026, 12, 15),
            dates_manually_adjusted=False,
        )

        db.add(task)

        with pytest.raises(IntegrityError):
            db.flush()

    finally:
        db.rollback()
        db.close()
