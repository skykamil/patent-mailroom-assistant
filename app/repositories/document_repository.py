from sqlalchemy.orm import Session

from app.db.models.document import Document

def create_document(db: Session, document: Document) -> Document:
    db.add(document)
    return document
