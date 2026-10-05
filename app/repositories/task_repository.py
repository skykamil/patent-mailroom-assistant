from sqlalchemy.orm import Session

from app.db.models.task import Task


def create_task(db: Session, task: Task) -> Task:
    db.add(task)
    return task
