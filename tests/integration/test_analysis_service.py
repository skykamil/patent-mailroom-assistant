import pytest

from sqlalchemy import func, select

from app.db.models.correspondence import Correspondence
from app.domain.correspondence import ImportType
from app.domain.exceptions import AnalysisNotFoundError, CorrespondenceNotFoundError
from app.services import analysis_service
from tests.integration.db import TestSessionLocal


def test_get_analysis_by_correspondence_id_raises_correspondence_not_found():
    db = TestSessionLocal()
    try:
        max_correspondence_id = db.scalar(
            select(func.max(Correspondence.id))
        ) or 0
        missing_correspondence_id = max_correspondence_id + 1

        with pytest.raises(
            CorrespondenceNotFoundError,
            match=f"Correspondence with id {missing_correspondence_id} not found",
        ):
            analysis_service.get_analysis_by_correspondence_id(db, missing_correspondence_id)
    finally:
        db.close()


def test_get_analysis_by_correspondence_id_raises_analysis_not_found():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        with pytest.raises(
            AnalysisNotFoundError,
            match=f"Analysis for correspondence with id {correspondence.id} not found",
        ):
            analysis_service.get_analysis_by_correspondence_id(db, correspondence.id)
    finally:
        db.rollback()
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()
