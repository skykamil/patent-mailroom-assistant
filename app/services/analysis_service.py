from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.domain.analysis import AnalysisStatus
from app.domain.exceptions import AnalysisAlreadyApprovedError, AnalysisNotFoundError, CorrespondenceCaseRequiredError, CorrespondenceNotFoundError, OfficeActionDueDateRequiredError
from app.domain.task import TaskType
from app.repositories import analysis_repository, correspondence_repository
from app.schemas.analysis import AnalysisCreate
from app.services import task_service


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
    if analysis.status == AnalysisStatus.APPROVED:
        return analysis
    if analysis.office_action_type is not None:
        if correspondence.case_id is None:
            raise CorrespondenceCaseRequiredError(
                f"Correspondence with id {correspondence_id} must be assigned to a case before creating tasks"
            )
        due_date = analysis.calculated_due_date or analysis.agent_reported_due_date
        if due_date is None:
            raise OfficeActionDueDateRequiredError(
                f"Analysis for correspondence with id {correspondence_id} must have a calculated or agent-reported due date before creating Office Action tasks"
            )
    try:
        approval_time = datetime.now(UTC)
        if analysis.office_action_type is not None:
            task_service.create_primary_task(
                db, correspondence_id, TaskType.OFFICE_ACTION,
                analysis.office_action_type, due_date,
            )
            task_service.create_review_task(
                db, correspondence_id, TaskType.REVIEW_OFFICE_ACTION,
                "Review Office Action", created_on=approval_time.date(),
            )
        analysis.status = AnalysisStatus.APPROVED
        analysis.approved_at = approval_time
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis
