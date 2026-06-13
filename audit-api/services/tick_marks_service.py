"""Tick marks (ISA 230): a firm-wide symbol/meaning library (which doubles as
the legend) and per-engagement applications of those marks to schedule lines
(trial-balance lines) or working papers, optionally annotated.

Managing the library needs Manager and above; applying a mark is open to all
signed-in staff. Applications validate that the mark exists and the target
belongs to the engagement.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Engagement,
    TickMark,
    TickMarkApplication,
    TrialBalance,
    TrialBalanceLine,
    WorkingPaper,
)
from models.tick_marks_models import (
    SEED_TICK_MARKS,
    SeedResult,
    TickMarkApplicationCreate,
    TickMarkApplicationRecord,
    TickMarkCreate,
    TickMarkRecord,
)
from services import audit_trail_service

LIBRARY_ENTITY = "tick_mark"
APPLICATION_ENTITY = "tick_mark_application"


# --- Firm library ---


async def list_tick_marks(session: AsyncSession) -> list[TickMarkRecord]:
    rows = await session.scalars(select(TickMark).order_by(TickMark.sort_order))
    return [TickMarkRecord.model_validate(row) for row in rows]


async def create_tick_mark(
    session: AsyncSession, *, actor: str, payload: TickMarkCreate
) -> TickMarkRecord:
    existing = await session.scalars(select(TickMark))
    if any(t.symbol == payload.symbol for t in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tick mark with symbol '{payload.symbol}' already exists",
        )
    mark = TickMark(
        id=uuid.uuid4(),
        symbol=payload.symbol,
        meaning=payload.meaning,
        sort_order=payload.sort_order,
    )
    session.add(mark)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=LIBRARY_ENTITY,
        entity_id=str(mark.id),
        after={"symbol": mark.symbol, "meaning": mark.meaning},
    )
    await session.commit()
    await session.refresh(mark)
    return TickMarkRecord.model_validate(mark)


async def seed_tick_marks(session: AsyncSession, *, actor: str) -> SeedResult:
    existing = {t.symbol for t in await session.scalars(select(TickMark))}
    created = 0
    for entry in SEED_TICK_MARKS:
        if entry["symbol"] in existing:
            continue
        session.add(TickMark(id=uuid.uuid4(), **entry))
        created += 1
    if created:
        audit_trail_service.record(
            session,
            actor=actor,
            action="create",
            entity_type=LIBRARY_ENTITY,
            entity_id="seed",
            after={"created": created},
        )
        await session.commit()
    return SeedResult(created=created, skipped=len(SEED_TICK_MARKS) - created)


# --- Engagement applications ---


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _validate_target(
    session: AsyncSession, engagement_id: uuid.UUID, target_type: str, target_id: uuid.UUID
) -> None:
    if target_type == "working_paper":
        wp = (
            await session.scalars(select(WorkingPaper).where(WorkingPaper.id == target_id))
        ).first()
        if wp is None or wp.engagement_id != engagement_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Working paper not found on this engagement",
            )
        return
    # trial_balance_line
    tb = (
        await session.scalars(
            select(TrialBalance).where(TrialBalance.engagement_id == engagement_id)
        )
    ).first()
    line = (
        await session.scalars(select(TrialBalanceLine).where(TrialBalanceLine.id == target_id))
    ).first()
    if tb is None or line is None or line.trial_balance_id != tb.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trial-balance line not found on this engagement",
        )


def _record(
    application: TickMarkApplication, marks: dict[uuid.UUID, TickMark]
) -> TickMarkApplicationRecord:
    record = TickMarkApplicationRecord.model_validate(application)
    mark = marks.get(application.tick_mark_id)
    if mark is not None:
        record.symbol = mark.symbol
        record.meaning = mark.meaning
    return record


async def _marks_by_id(session: AsyncSession) -> dict[uuid.UUID, TickMark]:
    return {m.id: m for m in await session.scalars(select(TickMark))}


async def list_applications(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
) -> list[TickMarkApplicationRecord]:
    await _get_engagement(session, engagement_id)
    rows = [
        r
        for r in await session.scalars(
            select(TickMarkApplication).where(TickMarkApplication.engagement_id == engagement_id)
        )
        if r.engagement_id == engagement_id
    ]
    if target_type is not None:
        rows = [r for r in rows if r.target_type == target_type]
    if target_id is not None:
        rows = [r for r in rows if r.target_id == target_id]
    marks = await _marks_by_id(session)
    return [_record(r, marks) for r in rows]


async def apply_tick_mark(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    payload: TickMarkApplicationCreate,
) -> TickMarkApplicationRecord:
    await _get_engagement(session, engagement_id)
    marks = await _marks_by_id(session)
    if payload.tick_mark_id not in marks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tick mark not found")
    await _validate_target(session, engagement_id, str(payload.target_type), payload.target_id)

    duplicate = [
        a
        for a in await session.scalars(select(TickMarkApplication))
        if a.tick_mark_id == payload.tick_mark_id
        and a.target_type == str(payload.target_type)
        and a.target_id == payload.target_id
    ]
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This tick mark is already applied to that item",
        )

    application = TickMarkApplication(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        tick_mark_id=payload.tick_mark_id,
        target_type=str(payload.target_type),
        target_id=payload.target_id,
        note=payload.note,
        applied_by=actor,
    )
    session.add(application)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=APPLICATION_ENTITY,
        entity_id=str(application.id),
        after={
            "tick_mark_id": str(application.tick_mark_id),
            "target_type": application.target_type,
            "target_id": str(application.target_id),
        },
    )
    await session.commit()
    await session.refresh(application)
    return _record(application, marks)


async def remove_application(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, application_id: uuid.UUID
) -> None:
    await _get_engagement(session, engagement_id)
    application = (
        await session.scalars(
            select(TickMarkApplication).where(TickMarkApplication.id == application_id)
        )
    ).first()
    if application is None or application.engagement_id != engagement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tick-mark application not found"
        )
    await session.delete(application)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=APPLICATION_ENTITY,
        entity_id=str(application_id),
        before={
            "tick_mark_id": str(application.tick_mark_id),
            "target_type": application.target_type,
            "target_id": str(application.target_id),
        },
    )
    await session.commit()
