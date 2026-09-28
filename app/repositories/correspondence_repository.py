from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence


def create_correspondence(db: Session, correspondence: Correspondence) -> Correspondence:
    db.add(correspondence)
    return correspondence


def get_correspondence_by_source_sha256(db: Session, source_sha256: str) -> Correspondence | None:
    statement = select(Correspondence).where(Correspondence.source_sha256 == source_sha256)
    return db.scalar(statement)
