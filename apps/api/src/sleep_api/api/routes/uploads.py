from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from sleep_api.core.exceptions import UploadValidationError
from sleep_api.dependencies import get_upload_repository
from sleep_api.infrastructure.uploads import LocalUploadRepository
from sleep_api.schemas.uploads import UploadResponse


router = APIRouter(tags=["cargas"])


@router.post("/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_edf(
    patient_name: Annotated[str, Form(min_length=1, max_length=120)],
    file: Annotated[UploadFile, File()],
    repository: Annotated[LocalUploadRepository, Depends(get_upload_repository)],
) -> UploadResponse:
    try:
        stored = await repository.save(patient_name, file)
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UploadResponse(
        upload_id=stored.upload_id,
        patient_name=stored.patient_name,
        original_filename=stored.original_filename,
        size_bytes=stored.size_bytes,
        created_at=stored.created_at,
    )

