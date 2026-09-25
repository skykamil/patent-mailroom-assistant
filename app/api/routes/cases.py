from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import CaseAlreadyExistsError
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
    except CaseAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
