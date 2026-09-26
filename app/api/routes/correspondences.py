from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import CaseNotFoundError
from app.schemas.correspondence import CorrespondenceRead
from app.services import correspondence_service
from app.services.correspondence_service import IncomingDocument


router = APIRouter()


@router.post(
    "/correspondences/direct-upload",
    response_model=CorrespondenceRead,
    status_code=status.HTTP_201_CREATED,
)
def import_direct_documents(
    files: list[UploadFile] = File(...),
    case_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    incoming_documents: list[IncomingDocument] = []
    for file in files:
        content = file.file.read()
        incoming_document = IncomingDocument(
            original_filename=file.filename or "uploaded_file",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
        incoming_documents.append(incoming_document)
    try:
        return correspondence_service.import_direct_documents(
            db=db,
            documents=incoming_documents,
            case_id=case_id,
        )
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
