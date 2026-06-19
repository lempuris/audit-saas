from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.firm_dashboard_models import FirmDashboard
from services import firm_dashboard_service

router = APIRouter(prefix="/api/firm-dashboard", tags=["firm-dashboard"])

# Firm-wide oversight is for those who run engagements; auditors get the
# personal dashboard (my-procedures / my review notes) instead.
Overseer = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=FirmDashboard)
async def get_firm_dashboard(_user: Overseer, db: Db) -> FirmDashboard:
    return await firm_dashboard_service.firm_dashboard(db)
