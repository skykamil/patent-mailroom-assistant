from sqlalchemy.orm import Session

from app.db.models.file import File


def create_file(db: Session, file: File) -> File:
    db.add(file)
    return file
