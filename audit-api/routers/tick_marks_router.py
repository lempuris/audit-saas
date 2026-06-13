import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.tick_marks_models import (
    SeedResult,
    TickMarkApplicationCreate,
    TickMarkApplicationRecord,
    TickMarkCreate,
    TickMarkRecord,
)
from services import tick_marks_service

library_router = APIRouter(prefix="/api/tick-marks", tags=["tick-marks"])
router = APIRouter(
    prefix="/api/engagements/{engagement_id}/tick-mark-applications", tags=["tick-marks"]
)

AnyStaff = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Curating the firm library is a Manager+ responsibility.
Manager = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@library_router.get("", response_model=list[TickMarkRecord])
async def list_tick_marks(_user: AnyStaff, db: Db) -> list[TickMarkRecord]:
    return await tick_marks_service.list_tick_marks(db)


@library_router.post("", response_model=TickMarkRecord, status_code=201)
async def create_tick_mark(body: TickMarkCreate, user: Manager, db: Db) -> TickMarkRecord:
    return await tick_marks_service.create_tick_mark(db, actor=user.user_id, payload=body)


@library_router.post("/seed", response_model=SeedResult)
async def seed_tick_marks(user: Manager, db: Db) -> SeedResult:
    return await tick_marks_service.seed_tick_marks(db, actor=user.user_id)


@router.get("", response_model=list[TickMarkApplicationRecord])
async def list_applications(
    engagement_id: uuid.UUID,
    _user: AnyStaff,
    db: Db,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
) -> list[TickMarkApplicationRecord]:
    return await tick_marks_service.list_applications(
        db, engagement_id, target_type=target_type, target_id=target_id
    )


@router.post("", response_model=TickMarkApplicationRecord, status_code=201)
async def apply_tick_mark(
    engagement_id: uuid.UUID, body: TickMarkApplicationCreate, user: AnyStaff, db: Db
) -> TickMarkApplicationRecord:
    return await tick_marks_service.apply_tick_mark(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_application(
    engagement_id: uuid.UUID, application_id: uuid.UUID, user: AnyStaff, db: Db
) -> None:
    await tick_marks_service.remove_application(
        db, actor=user.user_id, engagement_id=engagement_id, application_id=application_id
    )
