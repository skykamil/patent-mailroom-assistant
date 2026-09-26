from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.domain.exceptions import CaseNotFoundError
from app.schemas.correspondence import CorrespondenceRead
from app.schemas.document import DocumentUploadMetadata
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
        try:
            metadata = DocumentUploadMetadata(
                original_filename=file.filename or "uploaded_file",
                mime_type=file.content_type or "application/octet-stream"
            )
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors()) from exc
        content = file.file.read()
        incoming_document = IncomingDocument(
            original_filename=metadata.original_filename,
            content=content,
            mime_type=metadata.mime_type,
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
