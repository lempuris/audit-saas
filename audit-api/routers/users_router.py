from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.users_models import InviteRequest, RoleUpdateRequest, UserRecord
from services import users_service
from services.clerk_client import ClerkBackendClient, get_clerk_client

router = APIRouter(prefix="/api/users", tags=["users"])

AdminUser = Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN))]
Db = Annotated[AsyncSession, Depends(get_db)]
Clerk = Annotated[ClerkBackendClient, Depends(get_clerk_client)]


@router.get("", response_model=list[UserRecord])
async def list_users(_user: AdminUser, db: Db) -> list[UserRecord]:
    return await users_service.list_users(db)


@router.post("/invitations", status_code=status.HTTP_204_NO_CONTENT)
async def invite_user(body: InviteRequest, user: AdminUser, db: Db, clerk: Clerk) -> None:
    await users_service.invite_user(db, clerk, actor=user.user_id, email=body.email, role=body.role)


@router.patch("/{clerk_user_id}/role", response_model=UserRecord)
async def set_role(
    clerk_user_id: str, body: RoleUpdateRequest, user: AdminUser, db: Db, clerk: Clerk
) -> UserRecord:
    return await users_service.set_role(
        db, clerk, actor=user.user_id, clerk_user_id=clerk_user_id, role=body.role
    )


@router.post("/{clerk_user_id}/deactivate", response_model=UserRecord)
async def deactivate(clerk_user_id: str, user: AdminUser, db: Db, clerk: Clerk) -> UserRecord:
    return await users_service.set_active(
        db, clerk, actor=user.user_id, clerk_user_id=clerk_user_id, active=False
    )


@router.post("/{clerk_user_id}/reactivate", response_model=UserRecord)
async def reactivate(clerk_user_id: str, user: AdminUser, db: Db, clerk: Clerk) -> UserRecord:
    return await users_service.set_active(
        db, clerk, actor=user.user_id, clerk_user_id=clerk_user_id, active=True
    )
