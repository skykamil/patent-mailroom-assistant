import pytest
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.db.models.correspondence import Correspondence
from app.db.models.task import Task
from app.domain.correspondence import ImportType
from app.domain.task import TaskType
from tests.integration.db import TestSessionLocal


def test_task_belongs_to_correspondence():
    db = TestSessionLocal()

    try:
        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
        )
        db.add(correspondence)
        db.flush()

        task = Task(
            correspondence=correspondence,
            task_type=TaskType.REVIEW_OFFICE_ACTION,
            name="Review Office Action",
            is_primary=False,
            due_date=date(2026, 10, 15),
        )
        db.add(task)
        db.flush()

        assert task.id is not None
        assert task.correspondence_id == correspondence.id
        assert task.correspondence is correspondence
        assert task in correspondence.tasks

    finally:
        db.rollback()
        db.close()


def test_task_requires_correspondence():
    db = TestSessionLocal()

    try:
        task = Task(
            task_type=TaskType.REVIEW_OFFICE_ACTION,
            name="Review Office Action",
            is_primary=False,
            due_date=date(2026, 10, 15),
        )
        db.add(task)

        with pytest.raises(IntegrityError):
            db.flush()

    finally:
        db.rollback()
        db.close()


def test_review_agent_communication_task_belongs_to_correspondence():
    db = TestSessionLocal()

    try:
        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
        )
        db.add(correspondence)
        db.flush()

        task = Task(
            correspondence=correspondence,
            task_type=TaskType.REVIEW_AGENT_COMMUNICATION,
            name="Review agent communication",
            is_primary=False,
            due_date=date(2026, 10, 14),
        )
        db.add(task)
        db.flush()

        assert task.id is not None
        assert task.task_type == TaskType.REVIEW_AGENT_COMMUNICATION
        assert task.correspondence_id == correspondence.id
        assert task.is_primary is False

    finally:
        db.rollback()
        db.close()
