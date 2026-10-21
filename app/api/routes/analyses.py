from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import AnalysisNotFoundError, CorrespondenceNotFoundError
from app.schemas.analysis import AnalysisRead
from app.services import analysis_service


router = APIRouter()


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
