import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.archive_models import ArchiveRecord
from models.auth_models import AuthenticatedUser, Role
from services import archive_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/archive", tags=["archive"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=ArchiveRecord | None)
async def get_archive(engagement_id: uuid.UUID, _user: Reader, db: Db) -> ArchiveRecord | None:
    """The engagement's archive/retention record, or null if not yet archived."""
    return await archive_service.get_archive(db, engagement_id)
