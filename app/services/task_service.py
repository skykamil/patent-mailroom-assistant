from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.domain.task import TaskType
from app.repositories import task_repository


def create_review_task(
    db: Session,
    correspondence_id: int,
    task_type: TaskType,
    name: str,
    created_on: date,
    event_id: int | None = None,
) -> Task:
    due_date = created_on + timedelta(days=7)
    task = Task(
        is_primary=False,
        correspondence_id=correspondence_id,
        task_type=task_type,
        name=name,
        due_date=due_date,
        event_id=event_id
    )
    return task_repository.create_task(db, task)


def create_primary_task(
    db: Session,
    correspondence_id: int,
    event_id: int,
    task_type: TaskType,
    name: str,
    due_date: date,
) -> Task:
    task = Task(
        is_primary=True,
        correspondence_id=correspondence_id,
        event_id=event_id,
        task_type=task_type,
        name=name,
        due_date=due_date,
    )
    return task_repository.create_task(db, task)
