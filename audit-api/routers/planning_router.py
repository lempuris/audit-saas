import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.planning_models import (
    LeadSchedule,
    LeadScheduleSummary,
    MyProcedure,
    PlanningSummary,
)
from services import planning_service

router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["planning"])
me_router = APIRouter(prefix="/api/my-procedures", tags=["planning"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/lead-schedules", response_model=list[LeadScheduleSummary])
async def list_lead_schedules(
    engagement_id: uuid.UUID, _user: Reader, db: Db
) -> list[LeadScheduleSummary]:
    return await planning_service.list_lead_schedules(db, engagement_id)


@router.get("/lead-schedules/{fs_area}", response_model=LeadSchedule)
async def get_lead_schedule(
    engagement_id: uuid.UUID, fs_area: str, _user: Reader, db: Db
) -> LeadSchedule:
    return await planning_service.get_lead_schedule(db, engagement_id, fs_area)


@router.get("/planning-summary", response_model=PlanningSummary)
async def planning_summary(engagement_id: uuid.UUID, _user: Reader, db: Db) -> PlanningSummary:
    return await planning_service.planning_summary(db, engagement_id)


@me_router.get("", response_model=list[MyProcedure])
async def my_procedures(user: Reader, db: Db) -> list[MyProcedure]:
    return await planning_service.my_procedures(db, user_id=user.user_id)
