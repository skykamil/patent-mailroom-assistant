from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.case import Case

def create_case(db: Session, case: Case) -> Case:
    db.add(case)
    return case

def get_case_by_internal_reference(db: Session, internal_reference: str) -> Case | None:
    statement = select(Case).where(Case.internal_reference == internal_reference)
    return db.scalar(statement)

def get_case_by_id(db: Session, case_id: int) -> Case | None:
    statement = select(Case).where(Case.id == case_id)
    return db.scalar(statement)

def delete_case(db: Session, case: Case) -> None:
    db.delete(case)