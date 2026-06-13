import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.cross_references_models import CrossReferenceCreate, CrossReferenceRecord
from services import cross_references_service

router = APIRouter(
    prefix="/api/engagements/{engagement_id}/cross-references", tags=["cross-references"]
)

# Cross-referencing is part of fieldwork — all signed-in staff may link items.
AnyStaff = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[CrossReferenceRecord])
async def list_cross_references(
    engagement_id: uuid.UUID,
    _user: AnyStaff,
    db: Db,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
) -> list[CrossReferenceRecord]:
    return await cross_references_service.list_cross_references(
        db, engagement_id, source_type=source_type, source_id=source_id
    )


@router.post("", response_model=CrossReferenceRecord, status_code=201)
async def create_cross_reference(
    engagement_id: uuid.UUID, body: CrossReferenceCreate, user: AnyStaff, db: Db
) -> CrossReferenceRecord:
    return await cross_references_service.create_cross_reference(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cross_reference(
    engagement_id: uuid.UUID, reference_id: uuid.UUID, user: AnyStaff, db: Db
) -> None:
    await cross_references_service.delete_cross_reference(
        db, actor=user.user_id, engagement_id=engagement_id, reference_id=reference_id
    )
