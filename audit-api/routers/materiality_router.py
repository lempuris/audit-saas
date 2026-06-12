import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.materiality_models import MaterialityInput, MaterialityRecord
from services import materiality_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/materiality", tags=["materiality"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Approver = Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=MaterialityRecord)
async def get_materiality(engagement_id: uuid.UUID, _user: Reader, db: Db) -> MaterialityRecord:
    return await materiality_service.get_materiality(db, engagement_id)


@router.put("", response_model=MaterialityRecord)
async def upsert_materiality(
    engagement_id: uuid.UUID, body: MaterialityInput, user: Writer, db: Db
) -> MaterialityRecord:
    return await materiality_service.upsert_materiality(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.post("/approve", response_model=MaterialityRecord)
async def approve_materiality(
    engagement_id: uuid.UUID, user: Approver, db: Db
) -> MaterialityRecord:
    return await materiality_service.approve(db, actor=user.user_id, engagement_id=engagement_id)


@router.post("/reopen", response_model=MaterialityRecord)
async def reopen_materiality(engagement_id: uuid.UUID, user: Approver, db: Db) -> MaterialityRecord:
    return await materiality_service.reopen(db, actor=user.user_id, engagement_id=engagement_id)
