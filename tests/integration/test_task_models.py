import pytest
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.db.models.case import Case
from app.db.models.correspondence import Correspondence
from app.db.models.event import Event
from app.domain.analysis import EventType
from app.db.models.task import Task
from app.domain.correspondence import ImportType
from app.domain.task import TaskType
from tests.integration.db import TestSessionLocal


def test_task_can_exist_without_event():
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
        assert task.event_id is None
        assert task.correspondence is correspondence
        assert task in correspondence.tasks

    finally:
        db.rollback()
        db.close()


def test_task_can_be_linked_to_correspondence_and_event():
    db = TestSessionLocal()

    try:
        case = Case(
            internal_reference="PAT-CN-970",
            jurisdiction="CN",
        )
        db.add(case)
        db.flush()

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.flush()

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.flush()

        task = Task(
            correspondence=correspondence,
            event=event,
            task_type=TaskType.OFFICE_ACTION,
            name="Office Action response",
            is_primary=True,
            due_date=date(2027, 1, 15),
        )
        db.add(task)
        db.flush()

        assert task.id is not None
        assert task.correspondence_id == correspondence.id
        assert task.event_id == event.id
        assert task.correspondence is correspondence
        assert task.event is event
        assert task in correspondence.tasks
        assert task in event.tasks

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


def test_duplicate_primary_task_for_same_event_and_type_is_rejected():
    db = TestSessionLocal()

    try:
        case = Case(
            internal_reference="PAT-CN-971",
            jurisdiction="CN",
        )
        db.add(case)
        db.flush()

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.flush()

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.flush()

        first_task = Task(
            correspondence=correspondence,
            event=event,
            task_type=TaskType.OFFICE_ACTION,
            name="Office Action response",
            is_primary=True,
            due_date=date(2027, 1, 15),
        )
        db.add(first_task)
        db.flush()

        second_task = Task(
            correspondence=correspondence,
            event=event,
            task_type=TaskType.OFFICE_ACTION,
            name="Duplicate Office Action response",
            is_primary=True,
            due_date=date(2027, 1, 20),
        )
        db.add(second_task)

        with pytest.raises(IntegrityError):
            db.flush()

    finally:
        db.rollback()
        db.close()


def test_multiple_non_primary_tasks_for_same_event_and_type_are_allowed():
    db = TestSessionLocal()

    try:
        case = Case(
            internal_reference="PAT-CN-972",
            jurisdiction="CN",
        )
        db.add(case)
        db.flush()

        correspondence = Correspondence(
            import_type=ImportType.EMAIL,
            case_id=case.id,
        )
        db.add(correspondence)
        db.flush()

        event = Event(
            case_id=case.id,
            event_type=EventType.OFFICE_ACTION,
        )
        db.add(event)
        db.flush()

        first_task = Task(
            correspondence=correspondence,
            event=event,
            task_type=TaskType.REVIEW_OFFICE_ACTION,
            name="First review",
            is_primary=False,
            due_date=date(2026, 12, 15),
        )

        second_task = Task(
            correspondence=correspondence,
            event=event,
            task_type=TaskType.REVIEW_OFFICE_ACTION,
            name="Second review",
            is_primary=False,
            due_date=date(2027, 1, 5),
        )

        db.add_all([first_task, second_task])
        db.flush()

        assert first_task.id is not None
        assert second_task.id is not None
        assert first_task.event_id == event.id
        assert second_task.event_id == event.id

    finally:
        db.rollback()
        db.close()
