import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.review_notes_models import (
    ReviewNoteCreate,
    ReviewNoteRecord,
    ReviewNoteRespond,
)
from services import review_notes_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/review-notes", tags=["review-notes"])
me_router = APIRouter(prefix="/api/me/review-notes", tags=["review-notes"])

AnyStaff = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
# Raising notes is a reviewer responsibility.
Reviewer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@me_router.get("", response_model=list[ReviewNoteRecord])
async def my_review_notes(user: AnyStaff, db: Db, open_only: bool = True) -> list[ReviewNoteRecord]:
    return await review_notes_service.list_for_user(db, user_id=user.user_id, open_only=open_only)


@router.get("", response_model=list[ReviewNoteRecord])
async def list_notes(
    engagement_id: uuid.UUID,
    _user: AnyStaff,
    db: Db,
    note_status: str | None = None,
    assigned_to: str | None = None,
    working_paper_id: uuid.UUID | None = None,
) -> list[ReviewNoteRecord]:
    return await review_notes_service.list_notes(
        db,
        engagement_id,
        note_status=note_status,
        assigned_to=assigned_to,
        working_paper_id=working_paper_id,
    )


@router.post("", response_model=ReviewNoteRecord, status_code=201)
async def raise_note(
    engagement_id: uuid.UUID, body: ReviewNoteCreate, user: Reviewer, db: Db
) -> ReviewNoteRecord:
    return await review_notes_service.raise_note(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.patch("/{note_id}/respond", response_model=ReviewNoteRecord)
async def respond(
    engagement_id: uuid.UUID, note_id: uuid.UUID, body: ReviewNoteRespond, user: AnyStaff, db: Db
) -> ReviewNoteRecord:
    return await review_notes_service.respond(
        db, actor=user.user_id, engagement_id=engagement_id, note_id=note_id, payload=body
    )


@router.patch("/{note_id}/clear", response_model=ReviewNoteRecord)
async def clear_note(
    engagement_id: uuid.UUID, note_id: uuid.UUID, user: AnyStaff, db: Db
) -> ReviewNoteRecord:
    # The reviewer-or-author check is enforced in the service.
    return await review_notes_service.clear_note(
        db, user=user, engagement_id=engagement_id, note_id=note_id
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(engagement_id: uuid.UUID, note_id: uuid.UUID, user: AnyStaff, db: Db) -> None:
    await review_notes_service.delete_note(
        db, user=user, engagement_id=engagement_id, note_id=note_id
    )
