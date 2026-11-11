from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.domain.exceptions import InvalidEmailError
from app.schemas.review import ReviewPrepareResponse
from app.services.correspondence_service import IncomingDocument, prepare_incoming_documents


router = APIRouter()

@router.post(
    "/reviews/prepare",
    response_model=ReviewPrepareResponse,
)
def prepare_review(files: list[UploadFile] = File(), file_ids: list[UUID] = Form()):
    if len(files) != len(file_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Number of files and file IDs must match")
    if len(file_ids) != len(set(file_ids)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File IDs must be unique")
    documents = []
    for file, file_id in zip(files, file_ids):
        content = file.file.read()
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File name is required")
        documents.append(IncomingDocument(file_id=file_id, original_filename=file.filename, content=content, mime_type=file.content_type or "application/octet-stream"))
    try:
        prepared_documents = prepare_incoming_documents(documents)
    except InvalidEmailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ReviewPrepareResponse(files=prepared_documents)