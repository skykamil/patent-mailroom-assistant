from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.dependencies import get_db
from app.db.models.correspondence import Correspondence
from app.domain.correspondence import ImportType
from app.main import app
from tests.integration.db import TestSessionLocal


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def test_get_analysis_returns_404_when_correspondence_does_not_exist():
    db = TestSessionLocal()
    try:
        max_correspondence_id = (
            db.scalar(select(func.max(Correspondence.id))) or 0
        )
        missing_correspondence_id = max_correspondence_id + 1
    finally:
        db.close()
    response = client.get(f"/correspondences/{missing_correspondence_id}/analysis")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == (f"Correspondence with id {missing_correspondence_id} not found")


def test_get_analysis_returns_404_when_analysis_does_not_exist():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        response = client.get(f"/correspondences/{correspondence.id}/analysis")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Analysis for correspondence with id {correspondence.id} not found"
    finally:
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()
