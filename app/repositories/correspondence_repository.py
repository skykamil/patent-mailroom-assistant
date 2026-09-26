from sqlalchemy.orm import Session

from app.db.models.correspondence import Correspondence

def create_correspondence(db: Session, correspondence: Correspondence) -> Correspondence:
    db.add(correspondence)
    return correspondence
