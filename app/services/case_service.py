from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.db.models.case import Case
from app.domain.case_rules import derive_jurisdiction
from app.domain.exceptions import ApplicationNumberAlreadyExistsError, CaseAlreadyExistsError, CaseInUseError,  CaseNotFoundError
from app.repositories import case_repository
from app.schemas.case import CaseCreate, CaseUpdate

def create_case(db: Session, case_data: CaseCreate) -> Case:
    existing_case = case_repository.get_case_by_internal_reference(db, case_data.internal_reference)
    if existing_case is not None:
        raise CaseAlreadyExistsError(f"Case with internal reference {case_data.internal_reference} already exists")
    jurisdiction = derive_jurisdiction(case_data.internal_reference)
    case = Case(
        internal_reference=case_data.internal_reference,
        jurisdiction=jurisdiction,
        application_number=case_data.application_number,
        application_date=case_data.application_date,
        publication_number=case_data.publication_number,
        publication_date=case_data.publication_date,
        grant_number=case_data.grant_number,
        grant_date=case_data.grant_date,
        agent_reference=case_data.agent_reference
    )
    created_case = case_repository.create_case(db, case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if (
            isinstance(exc.orig, UniqueViolation)
            and exc.orig.diag.constraint_name == "uq_cases_jurisdiction_application_number"
            ):
            raise ApplicationNumberAlreadyExistsError(f"Application number {case_data.application_number} already exists in jurisdiction {jurisdiction}") from exc
        if (
            isinstance(exc.orig, UniqueViolation)
            and exc.orig.diag.constraint_name == "cases_internal_reference_key"
        ):
            raise CaseAlreadyExistsError(f"Case with internal reference {case_data.internal_reference} already exists") from exc
        raise
    db.refresh(created_case)
    return created_case

def get_case_by_id(db: Session, case_id: int) -> Case:
    case = case_repository.get_case_by_id(db, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case with id {case_id} not found")
    return case

def update_case(db: Session, case_id: int, case_data: CaseUpdate) -> Case:
    case = get_case_by_id(db, case_id)
    update_data = case_data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(case, field_name, value)
    attempted_application_number = case.application_number
    jurisdiction = case.jurisdiction
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if (
            isinstance(exc.orig, UniqueViolation)
            and exc.orig.diag.constraint_name == "uq_cases_jurisdiction_application_number"
        ):
            raise ApplicationNumberAlreadyExistsError(f"Application number {attempted_application_number} already exists in jurisdiction {jurisdiction}") from exc
        raise
    db.refresh(case)
    return case

def delete_case(db: Session, case_id: int) -> None:
    case = get_case_by_id(db, case_id)
    case_repository.delete_case(db, case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, ForeignKeyViolation):
            raise CaseInUseError(f"Case with id {case_id} cannot be deleted because it is in use") from exc
        raise
