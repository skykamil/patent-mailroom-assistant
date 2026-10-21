from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.domain.exceptions import AnalysisNotFoundError, CorrespondenceNotFoundError
from app.repositories import analysis_repository, correspondence_repository


def get_analysis_by_correspondence_id(db: Session, correspondence_id: int) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if analysis is None:
        raise AnalysisNotFoundError(f"Analysis for correspondence with id {correspondence_id} not found")
    return analysis
