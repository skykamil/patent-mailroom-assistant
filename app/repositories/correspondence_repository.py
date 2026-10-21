from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence


def create_correspondence(db: Session, correspondence: Correspondence) -> Correspondence:
    db.add(correspondence)
    return correspondence


def get_correspondence_by_id(db: Session, correspondence_id: int) -> Correspondence | None:
    statement = select(Correspondence).where(Correspondence.id == correspondence_id)
    return db.scalar(statement)


def get_correspondence_by_id_for_update(db: Session, correspondence_id: int) -> Correspondence | None:
    statement = select(Correspondence).where(Correspondence.id == correspondence_id).with_for_update()
    return db.scalar(statement)
