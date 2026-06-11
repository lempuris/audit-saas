from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.audit_trail_models import AuditTrailPage
from models.auth_models import AuthenticatedUser, Role
from services import audit_trail_service

router = APIRouter(prefix="/api/audit-trail", tags=["audit-trail"])


@router.get("", response_model=AuditTrailPage)
async def list_audit_trail(
    _user: Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditTrailPage:
    return await audit_trail_service.list_entries(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        limit=limit,
        offset=offset,
    )
