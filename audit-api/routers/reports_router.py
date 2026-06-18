import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.reports_models import ReportCreate, ReportRecord, ReportUpdate
from services import reports_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/reports", tags=["reports"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Drafting/editing reports is Manager and above; finalizing is enforced as
# Partner/Admin inside the service.
Manager = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
# Deleting a report (to start over with a different opinion) is Partner/Admin.
Partner = Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ReportRecord])
async def list_reports(engagement_id: uuid.UUID, _user: Reader, db: Db) -> list[ReportRecord]:
    return await reports_service.list_reports(db, engagement_id)


@router.post("", response_model=ReportRecord, status_code=201)
async def create_report(
    engagement_id: uuid.UUID, body: ReportCreate, user: Manager, db: Db
) -> ReportRecord:
    return await reports_service.create_report(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.get("/{report_id}", response_model=ReportRecord)
async def get_report(
    engagement_id: uuid.UUID, report_id: uuid.UUID, _user: Reader, db: Db
) -> ReportRecord:
    return await reports_service.get_report(db, engagement_id, report_id)


@router.patch("/{report_id}", response_model=ReportRecord)
async def update_report(
    engagement_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ReportUpdate,
    user: Manager,
    db: Db,
) -> ReportRecord:
    return await reports_service.update_report(
        db,
        actor=user.user_id,
        actor_role=user.role,
        engagement_id=engagement_id,
        report_id=report_id,
        payload=body,
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    engagement_id: uuid.UUID, report_id: uuid.UUID, user: Partner, db: Db
) -> None:
    await reports_service.delete_report(
        db, actor=user.user_id, engagement_id=engagement_id, report_id=report_id
    )
