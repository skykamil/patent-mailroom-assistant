from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import AnalysisAlreadyApprovedError, AnalysisEventSelectionUnresolvedError, AnalysisEventTypeRequiredError, AnalysisNotFoundError, CorrespondenceCaseRequiredError, CorrespondenceNotFoundError, EventCaseMismatchError, EventNotFoundError, EventTypeMismatchError, OfficeActionDueDateRequiredError
from app.schemas.analysis import AnalysisCreate, AnalysisEventSelectionUpdate, AnalysisRead
from app.services import analysis_service


router = APIRouter()


@router.put(
    "/correspondences/{correspondence_id}/analysis",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
def save_analysis(
    correspondence_id: int,
    analysis_data: AnalysisCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        result = analysis_service.save_analysis(db, correspondence_id, analysis_data)
    except CorrespondenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisAlreadyApprovedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return result.analysis


@router.get(
    "/correspondences/{correspondence_id}/analysis",
    response_model=AnalysisRead,
)
def get_analysis(correspondence_id: int, db: Session = Depends(get_db)):
    try:
        return analysis_service.get_analysis_by_correspondence_id(db, correspondence_id)
    except CorrespondenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/correspondences/{correspondence_id}/analysis/approve",
    response_model=AnalysisRead,
)
def approve_analysis(correspondence_id: int, db: Session = Depends(get_db)):
    try:
        return analysis_service.approve_analysis(db, correspondence_id)
    except CorrespondenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisEventSelectionUnresolvedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CorrespondenceCaseRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AnalysisEventTypeRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EventCaseMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EventTypeMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OfficeActionDueDateRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put(
    "/correspondences/{correspondence_id}/analysis/event-selection",
    response_model=AnalysisRead,
)
def update_analysis_event_selection(
    correspondence_id: int,
    selection_data: AnalysisEventSelectionUpdate,
    db: Session = Depends(get_db),
):
    try:
        analysis = analysis_service.update_analysis_event_selection(db, correspondence_id, selection_data)
        return analysis
    except CorrespondenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnalysisAlreadyApprovedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EventCaseMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EventTypeMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
