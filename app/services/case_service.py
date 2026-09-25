from sqlalchemy.orm import Session

from app.db.models.case import Case
from app.domain.case_rules import derive_jurisdiction
from app.repositories import case_repository
from app.schemas.case import CaseCreate

def create_case(db: Session, case_data: CaseCreate) -> Case:
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
    return case_repository.create_case(db, case)
