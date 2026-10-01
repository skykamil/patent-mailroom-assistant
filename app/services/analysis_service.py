from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.domain.exceptions import CorrespondenceNotFoundError
from app.repositories import analysis_repository, correspondence_repository
from app.schemas.analysis import AnalysisCreate

def create_analysis(
    db: Session,
    correspondence_id: int,
    analysis_data: AnalysisCreate,
) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    existing_analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if existing_analysis is not None:
        update_data = analysis_data.model_dump()
        for field_name, value in update_data.items():
            setattr(existing_analysis, field_name, value)
        db.commit()
        db.refresh(existing_analysis)
        return existing_analysis
    analysis_values = analysis_data.model_dump()
    analysis = Analysis(
        correspondence_id=correspondence_id,
        **analysis_values,
    )
    created_analysis = analysis_repository.create_analysis(db, analysis)
    db.commit()
    db.refresh(created_analysis)
    return created_analysis
