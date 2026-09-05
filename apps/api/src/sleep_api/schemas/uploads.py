from pydantic import BaseModel


class UploadResponse(BaseModel):
    upload_id: str
    patient_name: str
    original_filename: str
    size_bytes: int
    created_at: str
    status: str = "uploaded"

