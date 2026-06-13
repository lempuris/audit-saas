"""Review notes (ISA 220): a reviewer raises a note on a working paper (or the
engagement at large) and assigns it to a preparer; the preparer responds; a
reviewer (or the note's raiser) clears it. Status flows open → responded →
cleared.

Raising and clearing are reviewer actions (Manager and above, or — for clearing
— the note's raiser); responding is open to all staff so preparers can reply.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, ReviewNote, WorkingPaper
from models.auth_models import AuthenticatedUser, Role
from models.review_notes_models import (
    ReviewNoteCreate,
    ReviewNoteRecord,
    ReviewNoteRespond,
)
from services import audit_trail_service

ENTITY_TYPE = "review_note"
_REVIEWER_ROLES = {Role.ADMIN, Role.PARTNER, Role.MANAGER}


def _snapshot(note: ReviewNote) -> dict:
    return {
        "engagement_id": str(note.engagement_id),
        "working_paper_id": str(note.working_paper_id) if note.working_paper_id else None,
        "text": note.text,
        "assigned_to": note.assigned_to,
        "status": note.status,
        "response": note.response,
    }


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _get_note(
    session: AsyncSession, engagement_id: uuid.UUID, note_id: uuid.UUID
) -> ReviewNote:
    note = (await session.scalars(select(ReviewNote).where(ReviewNote.id == note_id))).first()
    if note is None or note.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review note not found")
    return note


async def list_notes(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    note_status: str | None = None,
    assigned_to: str | None = None,
    working_paper_id: uuid.UUID | None = None,
) -> list[ReviewNoteRecord]:
    await _get_engagement(session, engagement_id)
    rows = [
        r
        for r in await session.scalars(
            select(ReviewNote)
            .where(ReviewNote.engagement_id == engagement_id)
            .order_by(ReviewNote.created_at)
        )
        if r.engagement_id == engagement_id
    ]
    if note_status is not None:
        rows = [r for r in rows if r.status == note_status]
    if assigned_to is not None:
        rows = [r for r in rows if r.assigned_to == assigned_to]
    if working_paper_id is not None:
        rows = [r for r in rows if r.working_paper_id == working_paper_id]
    return [ReviewNoteRecord.model_validate(r) for r in rows]


async def list_for_user(
    session: AsyncSession, *, user_id: str, open_only: bool = True
) -> list[ReviewNoteRecord]:
    """Notes assigned to a user across engagements, for the open-notes dashboard."""
    rows = [
        r
        for r in await session.scalars(
            select(ReviewNote)
            .where(ReviewNote.assigned_to == user_id)
            .order_by(ReviewNote.created_at)
        )
        if r.assigned_to == user_id
    ]
    if open_only:
        rows = [r for r in rows if r.status != "cleared"]
    return [ReviewNoteRecord.model_validate(r) for r in rows]


async def raise_note(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: ReviewNoteCreate
) -> ReviewNoteRecord:
    await _get_engagement(session, engagement_id)
    if payload.working_paper_id is not None:
        wp = (
            await session.scalars(
                select(WorkingPaper).where(WorkingPaper.id == payload.working_paper_id)
            )
        ).first()
        if wp is None or wp.engagement_id != engagement_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Working paper not found on this engagement",
            )

    note = ReviewNote(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        working_paper_id=payload.working_paper_id,
        text=payload.text,
        raised_by=actor,
        assigned_to=payload.assigned_to,
        status="open",
    )
    session.add(note)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(note.id),
        after=_snapshot(note),
    )
    await session.commit()
    await session.refresh(note)
    return ReviewNoteRecord.model_validate(note)


async def respond(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: ReviewNoteRespond,
) -> ReviewNoteRecord:
    await _get_engagement(session, engagement_id)
    note = await _get_note(session, engagement_id, note_id)
    if note.status == "cleared":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cannot respond to a cleared note"
        )
    before = _snapshot(note)
    note.response = payload.response
    note.responded_by = actor
    note.responded_at = datetime.now(UTC)
    note.status = "responded"
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(note_id),
        before=before,
        after=_snapshot(note),
    )
    await session.commit()
    await session.refresh(note)
    return ReviewNoteRecord.model_validate(note)


async def clear_note(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    engagement_id: uuid.UUID,
    note_id: uuid.UUID,
) -> ReviewNoteRecord:
    await _get_engagement(session, engagement_id)
    note = await _get_note(session, engagement_id, note_id)

    if user.role not in _REVIEWER_ROLES and note.raised_by != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or the note's author can clear it",
        )

    before = _snapshot(note)
    note.status = "cleared"
    note.cleared_by = user.user_id
    note.cleared_at = datetime.now(UTC)
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(note_id),
        before=before,
        after=_snapshot(note),
    )
    await session.commit()
    await session.refresh(note)
    return ReviewNoteRecord.model_validate(note)


async def delete_note(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    engagement_id: uuid.UUID,
    note_id: uuid.UUID,
) -> None:
    await _get_engagement(session, engagement_id)
    note = await _get_note(session, engagement_id, note_id)
    if user.role not in _REVIEWER_ROLES and note.raised_by != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or the note's author can delete it",
        )
    await session.delete(note)
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(note_id),
        before=_snapshot(note),
    )
    await session.commit()
