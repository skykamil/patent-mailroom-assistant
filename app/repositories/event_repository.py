from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.event import Event


def get_event_by_id(db: Session, event_id: int) -> Event | None:
    statement = select(Event).where(Event.id == event_id)
    return db.scalar(statement)
