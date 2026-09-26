from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.db.models.case import Case

TEST_DATABASE_URL = "postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom_test"

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=test_engine)

def delete_case_by_internal_reference(internal_reference: str):
    db = TestSessionLocal()
    try:
        statement = delete(Case).where(Case.internal_reference == internal_reference)
        db.execute(statement)
        db.commit()
    finally:
        db.close()
