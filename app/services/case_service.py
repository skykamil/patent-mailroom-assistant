from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from psycopg.errors import UniqueViolation

from app.db.models.case import Case
from app.domain.case_rules import derive_jurisdiction
from app.domain.exceptions import ApplicationNumberAlreadyExistsError, CaseAlreadyExistsError
from app.repositories import case_repository
from app.schemas.case import CaseCreate

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
