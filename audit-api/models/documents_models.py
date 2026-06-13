import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PresignUploadRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    working_paper_id: uuid.UUID | None = None


class PresignUploadResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str


class DocumentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    working_paper_id: uuid.UUID | None
    filename: str
    content_type: str
    size_bytes: int | None
    status: str
    uploaded_by: str
    created_at: datetime
    updated_at: datetime


class DownloadResponse(BaseModel):
    download_url: str
