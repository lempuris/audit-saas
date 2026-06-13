import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.working_papers_models import (
    WorkingPaperCreate,
    WorkingPaperRecord,
    WorkingPaperStatusUpdate,
    WorkingPaperUpdate,
    WorkingPaperVersionRecord,
)
from services import working_papers_service

router = APIRouter(
    prefix="/api/engagements/{engagement_id}/working-papers", tags=["working-papers"]
)

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Auditors are first-class preparers of working papers.
Preparer = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Deleting a working paper is restricted to Manager and above.
Manager = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[WorkingPaperRecord])
async def list_working_papers(
    engagement_id: uuid.UUID,
    _user: Reader,
    db: Db,
    fs_area: str | None = None,
    wp_status: str | None = None,
) -> list[WorkingPaperRecord]:
    return await working_papers_service.list_working_papers(
        db, engagement_id, fs_area=fs_area, wp_status=wp_status
    )


@router.post("", response_model=WorkingPaperRecord, status_code=201)
async def create_working_paper(
    engagement_id: uuid.UUID, body: WorkingPaperCreate, user: Preparer, db: Db
) -> WorkingPaperRecord:
    return await working_papers_service.create_working_paper(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.get("/{wp_id}", response_model=WorkingPaperRecord)
async def get_working_paper(
    engagement_id: uuid.UUID, wp_id: uuid.UUID, _user: Reader, db: Db
) -> WorkingPaperRecord:
    return await working_papers_service.get_working_paper(db, engagement_id, wp_id)


@router.patch("/{wp_id}", response_model=WorkingPaperRecord)
async def update_working_paper(
    engagement_id: uuid.UUID, wp_id: uuid.UUID, body: WorkingPaperUpdate, user: Preparer, db: Db
) -> WorkingPaperRecord:
    return await working_papers_service.update_working_paper(
        db, actor=user.user_id, engagement_id=engagement_id, wp_id=wp_id, payload=body
    )


@router.patch("/{wp_id}/status", response_model=WorkingPaperRecord)
async def update_status(
    engagement_id: uuid.UUID,
    wp_id: uuid.UUID,
    body: WorkingPaperStatusUpdate,
    user: Preparer,
    db: Db,
) -> WorkingPaperRecord:
    return await working_papers_service.update_status(
        db, actor=user.user_id, engagement_id=engagement_id, wp_id=wp_id, payload=body
    )


@router.get("/{wp_id}/versions", response_model=list[WorkingPaperVersionRecord])
async def list_versions(
    engagement_id: uuid.UUID, wp_id: uuid.UUID, _user: Reader, db: Db
) -> list[WorkingPaperVersionRecord]:
    return await working_papers_service.list_versions(db, engagement_id, wp_id)


@router.delete("/{wp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_working_paper(
    engagement_id: uuid.UUID, wp_id: uuid.UUID, user: Manager, db: Db
) -> None:
    await working_papers_service.delete_working_paper(
        db, actor=user.user_id, engagement_id=engagement_id, wp_id=wp_id
    )
