from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.case import CaseCreate, CaseRead
from app.services import case_service

router = APIRouter()

@router.post("/cases", response_model=CaseRead)
def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db)
):
    return case_service.create_case(db, case_data)
