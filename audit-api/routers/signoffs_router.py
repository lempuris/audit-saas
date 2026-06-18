import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.signoffs_models import SignoffRecord, SignoffRequest
from services import signoffs_service

router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["sign-offs"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Reviewing/returning needs Manager and above; approving is further restricted
# to Partner/Admin inside the service (the action lives in the request body).
Reviewer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/working-papers/{wp_id}/sign-off", response_model=SignoffRecord, status_code=201)
async def sign_off_working_paper(
    engagement_id: uuid.UUID, wp_id: uuid.UUID, body: SignoffRequest, user: Reviewer, db: Db
) -> SignoffRecord:
    return await signoffs_service.sign_off_working_paper(
        db,
        actor=user.user_id,
        actor_role=user.role,
        engagement_id=engagement_id,
        wp_id=wp_id,
        payload=body,
    )


@router.post("/fs-areas/{fs_area}/sign-off", response_model=SignoffRecord, status_code=201)
async def sign_off_fs_area(
    engagement_id: uuid.UUID, fs_area: str, body: SignoffRequest, user: Reviewer, db: Db
) -> SignoffRecord:
    return await signoffs_service.sign_off_fs_area(
        db,
        actor=user.user_id,
        actor_role=user.role,
        engagement_id=engagement_id,
        fs_area=fs_area,
        payload=body,
    )


@router.get("/sign-offs", response_model=list[SignoffRecord])
async def list_sign_offs(
    engagement_id: uuid.UUID,
    _user: Reader,
    db: Db,
    target_type: str | None = None,
    target_id: str | None = None,
) -> list[SignoffRecord]:
    return await signoffs_service.list_sign_offs(
        db, engagement_id, target_type=target_type, target_id=target_id
    )
