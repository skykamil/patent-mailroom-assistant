from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.domain.analysis import AnalysisStatus, EventSelection
from app.domain.exceptions import AnalysisAlreadyApprovedError, AnalysisNotFoundError, CorrespondenceNotFoundError, EventCaseMismatchError, EventNotFoundError, EventTypeMismatchError
from app.repositories import analysis_repository, correspondence_repository, event_repository
from app.schemas.analysis import AnalysisCreate, AnalysisEventSelectionUpdate


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
        if existing_analysis.status == AnalysisStatus.APPROVED:
            raise AnalysisAlreadyApprovedError(
                f"Analysis for correspondence with id {correspondence_id} is already approved"
            )
        if existing_analysis.event_type != analysis_data.event_type:
            existing_analysis.event_selection = EventSelection.UNRESOLVED
            existing_analysis.event_id = None
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


def approve_analysis(db: Session, correspondence_id: int) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id_for_update(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if analysis is None:
        raise AnalysisNotFoundError(f"Analysis for correspondence with id {correspondence_id} not found")
    if analysis.status != AnalysisStatus.APPROVED:
        analysis.status = AnalysisStatus.APPROVED
        analysis.approved_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis


def update_analysis_event_selection(db: Session, correspondence_id: int, selection_data: AnalysisEventSelectionUpdate) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id_for_update(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError
    analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if analysis is None:
        raise AnalysisNotFoundError
    if analysis.status == AnalysisStatus.APPROVED:
        raise AnalysisAlreadyApprovedError
    if selection_data.event_selection == EventSelection.EXISTING_EVENT:
        assert selection_data.event_id is not None
        event = event_repository.get_event_by_id(db, selection_data.event_id)
        if event is None:
            raise EventNotFoundError
        if event.case_id != correspondence.case_id:
            raise EventCaseMismatchError
        if event.event_type != analysis.event_type:
            raise EventTypeMismatchError
    analysis.event_selection = selection_data.event_selection
    analysis.event_id = selection_data.event_id
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis
