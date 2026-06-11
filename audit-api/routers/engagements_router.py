import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.engagements_models import (
    EngagementCreate,
    EngagementDetail,
    EngagementRecord,
    EngagementUpdate,
    StatusChangeRequest,
    TeamMemberAdd,
    TeamMemberRecord,
)
from services import engagements_service

router = APIRouter(prefix="/api/engagements", tags=["engagements"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[EngagementRecord])
async def list_engagements(
    _user: Reader,
    db: Db,
    client_id: uuid.UUID | None = None,
    engagement_status: str | None = None,
) -> list[EngagementRecord]:
    return await engagements_service.list_engagements(
        db, client_id=client_id, engagement_status=engagement_status
    )


@router.get("/{engagement_id}", response_model=EngagementDetail)
async def get_engagement(engagement_id: uuid.UUID, _user: Reader, db: Db) -> EngagementDetail:
    return await engagements_service.get_engagement(db, engagement_id)


@router.post("", response_model=EngagementRecord, status_code=201)
async def create_engagement(body: EngagementCreate, user: Writer, db: Db) -> EngagementRecord:
    return await engagements_service.create_engagement(db, actor=user.user_id, payload=body)


@router.patch("/{engagement_id}", response_model=EngagementRecord)
async def update_engagement(
    engagement_id: uuid.UUID, body: EngagementUpdate, user: Writer, db: Db
) -> EngagementRecord:
    return await engagements_service.update_engagement(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.patch("/{engagement_id}/status", response_model=EngagementRecord)
async def change_status(
    engagement_id: uuid.UUID, body: StatusChangeRequest, user: Writer, db: Db
) -> EngagementRecord:
    # Completing additionally requires Partner/Admin — enforced in the service.
    return await engagements_service.change_status(
        db, user=user, engagement_id=engagement_id, payload=body
    )


@router.post("/{engagement_id}/team", response_model=TeamMemberRecord, status_code=201)
async def add_team_member(
    engagement_id: uuid.UUID, body: TeamMemberAdd, user: Writer, db: Db
) -> TeamMemberRecord:
    return await engagements_service.add_team_member(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.delete("/{engagement_id}/team/{clerk_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    engagement_id: uuid.UUID, clerk_user_id: str, user: Writer, db: Db
) -> None:
    await engagements_service.remove_team_member(
        db, actor=user.user_id, engagement_id=engagement_id, clerk_user_id=clerk_user_id
    )


@router.post("/{engagement_id}/team/confirm-independence", response_model=TeamMemberRecord)
async def confirm_independence(engagement_id: uuid.UUID, user: Reader, db: Db) -> TeamMemberRecord:
    return await engagements_service.confirm_independence(
        db, user=user, engagement_id=engagement_id
    )
