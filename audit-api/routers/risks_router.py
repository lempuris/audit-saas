import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.risks_models import RiskCreate, RiskRecord, RiskUpdate
from services import risks_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/risks", tags=["risks"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[RiskRecord])
async def list_risks(
    engagement_id: uuid.UUID,
    _user: Reader,
    db: Db,
    level: str | None = None,
    fs_area: str | None = None,
) -> list[RiskRecord]:
    return await risks_service.list_risks(db, engagement_id, level=level, fs_area=fs_area)


@router.get("/{risk_id}", response_model=RiskRecord)
async def get_risk(
    engagement_id: uuid.UUID, risk_id: uuid.UUID, _user: Reader, db: Db
) -> RiskRecord:
    return await risks_service.get_risk(db, engagement_id, risk_id)


@router.post("", response_model=RiskRecord, status_code=201)
async def create_risk(
    engagement_id: uuid.UUID, body: RiskCreate, user: Writer, db: Db
) -> RiskRecord:
    return await risks_service.create_risk(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.patch("/{risk_id}", response_model=RiskRecord)
async def update_risk(
    engagement_id: uuid.UUID, risk_id: uuid.UUID, body: RiskUpdate, user: Writer, db: Db
) -> RiskRecord:
    return await risks_service.update_risk(
        db, actor=user.user_id, engagement_id=engagement_id, risk_id=risk_id, payload=body
    )


@router.delete("/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk(engagement_id: uuid.UUID, risk_id: uuid.UUID, user: Writer, db: Db) -> None:
    await risks_service.delete_risk(
        db, actor=user.user_id, engagement_id=engagement_id, risk_id=risk_id
    )
