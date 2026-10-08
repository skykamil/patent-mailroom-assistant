from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.db.models.event import Event
from app.domain.analysis import AnalysisStatus, EventSelection, EventType, OfficeActionType
from app.domain.exceptions import AnalysisAlreadyApprovedError, AnalysisEventSelectionUnresolvedError, AnalysisEventTypeRequiredError, AnalysisNotFoundError, CorrespondenceCaseRequiredError, CorrespondenceNotFoundError, EventCaseMismatchError, EventNotFoundError, EventTypeMismatchError, OfficeActionDueDateRequiredError
from app.domain.task import TaskType
from app.repositories import analysis_repository, correspondence_repository, event_repository
from app.schemas.analysis import AnalysisCreate, AnalysisEventSelectionUpdate
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
    if analysis.status == AnalysisStatus.APPROVED:
        return analysis
    if analysis.event_selection == EventSelection.UNRESOLVED:
        raise AnalysisEventSelectionUnresolvedError(f"Analysis for correspondence with id {correspondence_id} has unresolved event selection")
    if analysis.event_selection == EventSelection.EXISTING_EVENT:
        assert analysis.event_id is not None
        event = event_repository.get_event_by_id(db, analysis.event_id)
        if event is None:
            raise EventNotFoundError(f"Event with id {analysis.event_id} not found")
        if event.case_id != correspondence.case_id:
            raise EventCaseMismatchError(f"Event with id {event.id} does not belong to the correspondence case")
        if event.event_type != analysis.event_type:
            raise EventTypeMismatchError(f"Event with id {event.id} does not match the analysis event type")
    if analysis.event_selection == EventSelection.NEW_EVENT:
        if correspondence.case_id is None:
            raise CorrespondenceCaseRequiredError(f"Correspondence with id {correspondence_id} must be assigned to a case before creating a new event")
        if analysis.event_type is None:
            raise AnalysisEventTypeRequiredError(f"Analysis for correspondence with id {correspondence_id} must have an event type before creating a new event")
        if analysis.event_type == EventType.OFFICE_ACTION:
            if analysis.calculated_due_date is not None:
                office_action_due_date = analysis.calculated_due_date
            elif analysis.agent_reported_due_date is not None:
                office_action_due_date = analysis.agent_reported_due_date
            else:
                raise OfficeActionDueDateRequiredError(f"Analysis for correspondence with id {correspondence_id} must have a calculated or agent-reported due date before creating a new Office Action event")
    try:
        approval_time = datetime.now(UTC)
        if analysis.event_selection == EventSelection.NEW_EVENT:
            new_event = Event(
                case_id=correspondence.case_id,
                event_type=analysis.event_type,
            )
            event_repository.create_event(db, new_event)
            db.flush()
            analysis.event_id = new_event.id
            if new_event.event_type == EventType.OFFICE_ACTION:
                if analysis.office_action_type is not None:
                    office_action_task_name = analysis.office_action_type
                else:
                    office_action_task_name = OfficeActionType.OFFICE_ACTION
                task_service.create_primary_task(
                    db,
                    correspondence_id,
                    new_event.id,
                    TaskType.OFFICE_ACTION,
                    office_action_task_name,
                    office_action_due_date,
                )
                task_service.create_review_task(
                    db,
                    correspondence_id,
                    TaskType.REVIEW_OFFICE_ACTION,
                    "Review Office Action",
                    created_on=approval_time.date(),
                    event_id=new_event.id,
                )
        analysis.status = AnalysisStatus.APPROVED
        analysis.approved_at = approval_time
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis


def update_analysis_event_selection(db: Session, correspondence_id: int, selection_data: AnalysisEventSelectionUpdate) -> Analysis:
    correspondence = correspondence_repository.get_correspondence_by_id_for_update(db, correspondence_id)
    if correspondence is None:
        raise CorrespondenceNotFoundError(f"Correspondence with id {correspondence_id} not found")
    analysis = analysis_repository.get_analysis_by_correspondence_id(db, correspondence_id)
    if analysis is None:
        raise AnalysisNotFoundError(f"Analysis for correspondence with id {correspondence_id} not found")
    if analysis.status == AnalysisStatus.APPROVED:
        raise AnalysisAlreadyApprovedError(f"Analysis for correspondence with id {correspondence_id} is already approved")
    if selection_data.event_selection == EventSelection.EXISTING_EVENT:
        assert selection_data.event_id is not None
        event = event_repository.get_event_by_id(db, selection_data.event_id)
        if event is None:
            raise EventNotFoundError(f"Event with id {selection_data.event_id} not found")
        if event.case_id != correspondence.case_id:
            raise EventCaseMismatchError(f"Event with id {selection_data.event_id} does not belong to the correspondence case")
        if event.event_type != analysis.event_type:
            raise EventTypeMismatchError(f"Event with id {selection_data.event_id} does not match the analysis event type")
    analysis.event_selection = selection_data.event_selection
    analysis.event_id = selection_data.event_id
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(analysis)
    return analysis
