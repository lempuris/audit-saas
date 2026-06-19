import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.completion_models import (
    ChecklistItemRecord,
    ChecklistItemUpdate,
    CompletionReadiness,
)
from services import completion_service

router = APIRouter(
    prefix="/api/engagements/{engagement_id}/completion-checklist", tags=["completion-checklist"]
)

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Seeding and resolving items is Manager and above.
Manager = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ChecklistItemRecord])
async def list_items(engagement_id: uuid.UUID, _user: Reader, db: Db) -> list[ChecklistItemRecord]:
    return await completion_service.list_items(db, engagement_id)


@router.get("/readiness", response_model=CompletionReadiness)
async def readiness(engagement_id: uuid.UUID, _user: Reader, db: Db) -> CompletionReadiness:
    return await completion_service.readiness(db, engagement_id)


@router.post("/seed", response_model=list[ChecklistItemRecord], status_code=201)
async def seed_standard(
    engagement_id: uuid.UUID, user: Manager, db: Db
) -> list[ChecklistItemRecord]:
    return await completion_service.seed_standard(
        db, actor=user.user_id, engagement_id=engagement_id
    )


@router.patch("/{item_id}", response_model=ChecklistItemRecord)
async def update_item(
    engagement_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ChecklistItemUpdate,
    user: Manager,
    db: Db,
) -> ChecklistItemRecord:
    return await completion_service.update_item(
        db, actor=user.user_id, engagement_id=engagement_id, item_id=item_id, payload=body
    )
