from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import AnalysisNotFoundError, CorrespondenceNotFoundError
from app.schemas.analysis import AnalysisCreate, AnalysisRead
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
