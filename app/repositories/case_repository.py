from sqlalchemy.orm import Session

from app.db.models.case import Case

def create_case(
    db: Session,
    case: Case
) -> Case:
    db.add(case)
    db.commit()
    db.refresh(case)
    return case