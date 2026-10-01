from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis


def get_analysis_by_correspondence_id(db: Session, correspondence_id: int) -> Analysis | None:
    statement = select(Analysis).where(Analysis.correspondence_id == correspondence_id)
    return db.scalar(statement)


def create_analysis(db: Session, analysis: Analysis) -> Analysis:
    db.add(analysis)
    return analysis