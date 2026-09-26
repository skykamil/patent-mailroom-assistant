from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import ApplicationNumberAlreadyExistsError, CaseAlreadyExistsError, CaseNotFoundError
from app.schemas.case import CaseCreate, CaseRead
from app.services import case_service

router = APIRouter()

@router.post(
    "/cases",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    try:
        return case_service.create_case(db, case_data)
    except ApplicationNumberAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CaseAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

@router.get(
    "/cases/{case_id}",
    response_model=CaseRead
)
def get_case(case_id: int, db: Session = Depends(get_db)):
    try:
        return case_service.get_case_by_id(db, case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))