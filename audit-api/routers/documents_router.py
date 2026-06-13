import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.documents_models import (
    DocumentRecord,
    DownloadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from services import documents_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/documents", tags=["documents"])

# All signed-in staff handle evidence; deletion is narrowed in the service to
# the uploader or a manager.
AnyStaff = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/presign-upload", response_model=PresignUploadResponse)
async def presign_upload(
    engagement_id: uuid.UUID, body: PresignUploadRequest, user: AnyStaff, db: Db
) -> PresignUploadResponse:
    return await documents_service.presign_upload(
        db,
        actor=user.user_id,
        engagement_id=engagement_id,
        filename=body.filename,
        content_type=body.content_type,
        working_paper_id=body.working_paper_id,
    )


@router.post("/{document_id}/confirm", response_model=DocumentRecord, status_code=201)
async def confirm_upload(
    engagement_id: uuid.UUID, document_id: uuid.UUID, user: AnyStaff, db: Db
) -> DocumentRecord:
    return await documents_service.confirm_upload(
        db, actor=user.user_id, engagement_id=engagement_id, document_id=document_id
    )


@router.get("", response_model=list[DocumentRecord])
async def list_documents(
    engagement_id: uuid.UUID,
    _user: AnyStaff,
    db: Db,
    working_paper_id: uuid.UUID | None = None,
) -> list[DocumentRecord]:
    return await documents_service.list_documents(
        db, engagement_id, working_paper_id=working_paper_id
    )


@router.get("/{document_id}/download", response_model=DownloadResponse)
async def download_document(
    engagement_id: uuid.UUID, document_id: uuid.UUID, user: AnyStaff, db: Db
) -> DownloadResponse:
    url = await documents_service.download_url(
        db, actor=user.user_id, engagement_id=engagement_id, document_id=document_id
    )
    return DownloadResponse(download_url=url)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    engagement_id: uuid.UUID, document_id: uuid.UUID, user: AnyStaff, db: Db
) -> None:
    await documents_service.delete_document(
        db, user=user, engagement_id=engagement_id, document_id=document_id
    )
