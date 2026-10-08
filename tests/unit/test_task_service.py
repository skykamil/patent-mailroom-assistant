from datetime import date
from unittest.mock import Mock

from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.domain.task import TaskType
from app.services import task_service


def test_create_review_task_creates_non_primary_task_due_in_seven_days(monkeypatch):
    db = Mock(spec=Session)
    repository_result = object()
    create_task_mock = Mock(return_value=repository_result)

    monkeypatch.setattr(
        task_service.task_repository,
        "create_task",
        create_task_mock,
    )

    result = task_service.create_review_task(
        db=db,
        correspondence_id=123,
        task_type=TaskType.REVIEW_AGENT_COMMUNICATION,
        name="Review agent communication",
        created_on=date(2026, 10, 7),
    )

    create_task_mock.assert_called_once()

    called_db, task = create_task_mock.call_args.args

    assert called_db is db
    assert isinstance(task, Task)
    assert task.correspondence_id == 123
    assert task.event_id is None
    assert task.task_type == TaskType.REVIEW_AGENT_COMMUNICATION
    assert task.name == "Review agent communication"
    assert task.is_primary is False
    assert task.due_date == date(2026, 10, 14)
    assert result is repository_result


def test_create_review_task_passes_event_id_to_task(monkeypatch):
    db = Mock(spec=Session)
    create_task_mock = Mock()

    monkeypatch.setattr(
        task_service.task_repository,
        "create_task",
        create_task_mock,
    )

    task_service.create_review_task(
        db=db,
        correspondence_id=123,
        task_type=TaskType.REVIEW_OFFICE_ACTION,
        name="Review Office Action",
        created_on=date(2026, 10, 7),
        event_id=456,
    )

    create_task_mock.assert_called_once()

    _, task = create_task_mock.call_args.args

    assert task.correspondence_id == 123
    assert task.event_id == 456
    assert task.task_type == TaskType.REVIEW_OFFICE_ACTION
    assert task.is_primary is False
    assert task.due_date == date(2026, 10, 14)
