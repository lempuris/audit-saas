"""Evidence documents (ISA 230/500): uploaded to S3 via presigned URLs and
optionally attached to the working paper they evidence.

Upload is two-step so the file never passes through the API: the client asks
for a presigned PUT URL (a 'pending' row is created), uploads straight to S3,
then confirms — at which point a HEAD fills in size + version id, the row goes
'available', and the create is logged. Downloads issue a presigned GET and log
an access ('read') row, so evidence access is auditable. Deleting is limited
to the uploader or Manager and above, and blocked on completed engagements.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Document, Engagement, WorkingPaper
from models.auth_models import AuthenticatedUser, Role
from models.documents_models import DocumentRecord, PresignUploadResponse
from models.engagements_models import EngagementStatus
from services import audit_trail_service, s3_client

ENTITY_TYPE = "document"
_MANAGER_ROLES = {Role.ADMIN, Role.PARTNER, Role.MANAGER}


def _snapshot(doc: Document) -> dict:
    return {
        "engagement_id": str(doc.engagement_id),
        "working_paper_id": str(doc.working_paper_id) if doc.working_paper_id else None,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "s3_key": doc.s3_key,
        "status": doc.status,
    }


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


def _require_not_completed(engagement: Engagement) -> None:
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify documents of a completed engagement",
        )


async def _get_document(
    session: AsyncSession, engagement_id: uuid.UUID, document_id: uuid.UUID
) -> Document:
    doc = (await session.scalars(select(Document).where(Document.id == document_id))).first()
    if doc is None or doc.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


async def _validate_working_paper(
    session: AsyncSession, engagement_id: uuid.UUID, working_paper_id: uuid.UUID
) -> None:
    wp = (
        await session.scalars(select(WorkingPaper).where(WorkingPaper.id == working_paper_id))
    ).first()
    if wp is None or wp.engagement_id != engagement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Working paper not found on this engagement",
        )


async def presign_upload(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    filename: str,
    content_type: str,
    working_paper_id: uuid.UUID | None,
) -> PresignUploadResponse:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    if working_paper_id is not None:
        await _validate_working_paper(session, engagement_id, working_paper_id)

    document_id = uuid.uuid4()
    s3_key = f"engagements/{engagement_id}/documents/{document_id}/{filename}"
    doc = Document(
        id=document_id,
        engagement_id=engagement_id,
        working_paper_id=working_paper_id,
        filename=filename,
        content_type=content_type,
        s3_key=s3_key,
        status="pending",
        uploaded_by=actor,
    )
    session.add(doc)
    await session.commit()
    upload_url = s3_client.presigned_put(s3_key, content_type)
    return PresignUploadResponse(document_id=document_id, upload_url=upload_url)


async def confirm_upload(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, document_id: uuid.UUID
) -> DocumentRecord:
    await _get_engagement(session, engagement_id)
    doc = await _get_document(session, engagement_id, document_id)

    info = s3_client.head(doc.s3_key)
    doc.size_bytes = info.get("size_bytes")
    doc.s3_version_id = info.get("version_id")
    doc.status = "available"
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(doc.id),
        after=_snapshot(doc),
    )
    await session.commit()
    await session.refresh(doc)
    return DocumentRecord.model_validate(doc)


async def list_documents(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    working_paper_id: uuid.UUID | None = None,
) -> list[DocumentRecord]:
    await _get_engagement(session, engagement_id)
    query = (
        select(Document)
        .where(Document.engagement_id == engagement_id)
        .order_by(Document.created_at)
    )
    if working_paper_id is not None:
        query = query.where(Document.working_paper_id == working_paper_id)
    rows = await session.scalars(query)
    docs = [d for d in rows if d.engagement_id == engagement_id]
    if working_paper_id is not None:
        docs = [d for d in docs if d.working_paper_id == working_paper_id]
    return [DocumentRecord.model_validate(d) for d in docs]


async def download_url(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, document_id: uuid.UUID
) -> str:
    await _get_engagement(session, engagement_id)
    doc = await _get_document(session, engagement_id, document_id)
    if doc.status != "available":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Document upload is not complete"
        )
    url = s3_client.presigned_get(doc.s3_key, doc.filename)
    # Evidence access is auditable.
    audit_trail_service.record(
        session,
        actor=actor,
        action="read",
        entity_type=ENTITY_TYPE,
        entity_id=str(doc.id),
    )
    await session.commit()
    return url


async def delete_document(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    engagement_id: uuid.UUID,
    document_id: uuid.UUID,
) -> None:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    doc = await _get_document(session, engagement_id, document_id)

    if user.role not in _MANAGER_ROLES and doc.uploaded_by != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or a manager can delete this document",
        )

    s3_client.delete(doc.s3_key)
    await session.delete(doc)
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(document_id),
        before=_snapshot(doc),
    )
    await session.commit()
