from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.api.dependencies import get_db
from app.db.models.analysis import Analysis
from app.db.models.correspondence import Correspondence
from app.domain.analysis import AnalysisStatus, EventType, OfficeActionType
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


def test_put_analysis_creates_analysis():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "application_number": "202611111111.1",
                "event_type": EventType.OFFICE_ACTION.value,
                "office_action_type": OfficeActionType.OFFICE_ACTION_4MO.value,
                "document_date": "2026-09-15",
                "agent_notification_date": "2026-09-18",
                "agent_reported_due_date": "2027-01-15",
                "calculated_due_date": "2027-01-15",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["correspondence_id"] == correspondence.id
        assert response_data["internal_reference"] == "PAT-CN-001"
        assert response_data["jurisdiction"] == "CN"
        assert response_data["application_number"] == "202611111111.1"
        assert response_data["event_type"] == EventType.OFFICE_ACTION.value
        assert response_data["office_action_type"] == OfficeActionType.OFFICE_ACTION_4MO.value
        assert response_data["agent_reported_due_date"] == "2027-01-15"
        assert response_data["status"] == AnalysisStatus.PENDING_REVIEW.value
        assert response_data["approved_at"] is None
    finally:
        if correspondence is not None:
            db.execute(delete(Analysis).where(Analysis.correspondence_id == correspondence.id))
            db.delete(correspondence)
        db.commit()
        db.close()


def test_put_analysis_updates_existing_analysis():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        first_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "application_number": "202611111111.1",
                "event_type": EventType.OFFICE_ACTION.value,
                "office_action_type": OfficeActionType.OFFICE_ACTION_4MO.value,
                "agent_reported_due_date": "2027-01-15",
            },
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        first_analysis_id = first_response.json()["id"]
        second_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "application_number": "202611111111.1",
                "event_type": EventType.OFFICE_ACTION.value,
                "office_action_type": OfficeActionType.OFFICE_ACTION_4MO.value,
                "agent_reported_due_date": None,
            },
        )
        assert second_response.status_code == status.HTTP_200_OK
        response_data = second_response.json()
        assert response_data["id"] == first_analysis_id
        assert response_data["agent_reported_due_date"] is None
        analysis_count = db.scalar(
            select(func.count())
            .select_from(Analysis)
            .where(Analysis.correspondence_id == correspondence.id)
        )
        assert analysis_count == 1
    finally:
        if correspondence is not None:
            db.execute(delete(Analysis).where(Analysis.correspondence_id == correspondence.id))
            db.delete(correspondence)
        db.commit()
        db.close()


def test_put_analysis_returns_404_when_correspondence_does_not_exist():
    db = TestSessionLocal()
    try:
        max_correspondence_id = (
            db.scalar(select(func.max(Correspondence.id))) or 0
        )
        missing_correspondence_id = max_correspondence_id + 1
    finally:
        db.close()
    response = client.put(
        f"/correspondences/{missing_correspondence_id}/analysis",
        json={
            "internal_reference": "PAT-CN-001",
            "jurisdiction": "CN",
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == (
        f"Correspondence with id {missing_correspondence_id} not found"
    )


def test_put_analysis_returns_422_for_invalid_event_type():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "event_type": "not_a_real_event_type",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        analysis_count = db.scalar(
            select(func.count())
            .select_from(Analysis)
            .where(Analysis.correspondence_id == correspondence.id)
        )
        assert analysis_count == 0
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()


def test_get_analysis_returns_analysis():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
            },
        )
        assert put_response.status_code == status.HTTP_201_CREATED
        analysis_id = put_response.json()["id"]
        response = client.get(f"/correspondences/{correspondence.id}/analysis")
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == analysis_id
        assert response_data["correspondence_id"] == correspondence.id
        assert response_data["internal_reference"] == "PAT-CN-001"
        assert response_data["jurisdiction"] == "CN"
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()


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


def test_put_analysis_returns_422_for_unknown_field_without_changing_existing_analysis():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        first_put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "agent_reported_due_date": "2027-01-15",
            },
        )
        assert first_put_response.status_code == status.HTTP_201_CREATED
        analysis_id = first_put_response.json()["id"]
        second_put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "agent_reported_due_date": "2027-02-15",
                "unexpected_field": "synthetic",
            },
        )
        assert second_put_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        get_response = client.get(f"/correspondences/{correspondence.id}/analysis")
        assert get_response.status_code == status.HTTP_200_OK
        response_data = get_response.json()
        assert response_data["id"] == analysis_id
        assert response_data["agent_reported_due_date"] == "2027-01-15"
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()


def test_post_approve_analysis_returns_approved_analysis():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
            },
        )
        assert put_response.status_code == status.HTTP_201_CREATED
        response = client.post(f"/correspondences/{correspondence.id}/analysis/approve")
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == AnalysisStatus.APPROVED.value
        assert response_data["approved_at"] is not None
        assert response_data["correspondence_id"] == correspondence.id
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()


def test_post_approve_analysis_does_not_change_approved_at_when_already_approved():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
            },
        )
        assert put_response.status_code == status.HTTP_201_CREATED
        first_response = client.post(f"/correspondences/{correspondence.id}/analysis/approve")
        assert first_response.status_code == status.HTTP_200_OK
        first_approved_at = first_response.json()["approved_at"]
        assert first_approved_at is not None
        second_response = client.post(f"/correspondences/{correspondence.id}/analysis/approve")
        assert second_response.status_code == status.HTTP_200_OK
        assert second_response.json()["status"] == AnalysisStatus.APPROVED.value
        assert second_response.json()["approved_at"] == first_approved_at
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()


def test_post_approve_analysis_returns_404_when_correspondence_does_not_exist():
    db = TestSessionLocal()
    try:
        max_correspondence_id = (
            db.scalar(select(func.max(Correspondence.id))) or 0
        )
        missing_correspondence_id = max_correspondence_id + 1
    finally:
        db.close()
    response = client.post(f"/correspondences/{missing_correspondence_id}/analysis/approve")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == (f"Correspondence with id {missing_correspondence_id} not found")


def test_post_approve_analysis_returns_404_when_analysis_does_not_exist():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        response = client.post(f"/correspondences/{correspondence.id}/analysis/approve")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == (f"Analysis for correspondence with id {correspondence.id} not found")
    finally:
        if correspondence is not None:
            db.delete(correspondence)
        db.commit()
        db.close()


def test_put_analysis_returns_409_when_analysis_is_already_approved():
    db = TestSessionLocal()
    correspondence = None
    try:
        correspondence = Correspondence(import_type=ImportType.EMAIL)
        db.add(correspondence)
        db.commit()
        db.refresh(correspondence)
        first_put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "agent_reported_due_date": "2027-01-15",
            },
        )
        assert first_put_response.status_code == status.HTTP_201_CREATED
        approve_response = client.post(f"/correspondences/{correspondence.id}/analysis/approve")
        assert approve_response.status_code == status.HTTP_200_OK
        second_put_response = client.put(
            f"/correspondences/{correspondence.id}/analysis",
            json={
                "internal_reference": "PAT-CN-001",
                "jurisdiction": "CN",
                "agent_reported_due_date": "2027-02-15",
            },
        )
        assert second_put_response.status_code == status.HTTP_409_CONFLICT
        assert second_put_response.json()["detail"] == (
            f"Analysis for correspondence with id {correspondence.id} is already approved"
        )
        get_response = client.get(f"/correspondences/{correspondence.id}/analysis")
        assert get_response.status_code == status.HTTP_200_OK
        response_data = get_response.json()
        assert response_data["status"] == AnalysisStatus.APPROVED.value
        assert response_data["agent_reported_due_date"] == "2027-01-15"
    finally:
        if correspondence is not None:
            db.execute(
                delete(Analysis).where(
                    Analysis.correspondence_id == correspondence.id
                )
            )
            db.delete(correspondence)
        db.commit()
        db.close()
