from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.domain.exceptions import AnalysisNotFoundError, CorrespondenceNotFoundError
from app.repositories import analysis_repository, correspondence_repository
from app.schemas.analysis import AnalysisCreate


@dataclass
class AnalysisSaveResult:
    analysis: Analysis
    created: bool


def save_analysis(
    db: Session,
    correspondence_id: int,
    analysis_data: AnalysisCreate,
) -> AnalysisSaveResult:
    correspondence = correspondence_repository.get_correspondence_by_id_for_update(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    existing_analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if existing_analysis is not None:
        update_data = analysis_data.model_dump()
        for field_name, value in update_data.items():
            setattr(existing_analysis, field_name, value)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(existing_analysis)
        return AnalysisSaveResult(
            analysis=existing_analysis,
            created=False,
        )
    analysis_values = analysis_data.model_dump()
    analysis = Analysis(
        correspondence_id=correspondence_id,
        **analysis_values,
    )
    created_analysis = analysis_repository.create_analysis(db, analysis)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(created_analysis)
    return AnalysisSaveResult(
        analysis=created_analysis,
        created=True,
    )


def get_analysis_by_correspondence_id(db: Session, correspondence_id: int) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if analysis is None:
        raise AnalysisNotFoundError(f"Analysis for correspondence with id {correspondence_id} not found")
    return analysis
