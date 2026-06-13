"""Working papers (ISA 230): per-engagement, FS-area-indexed records of
fieldwork, structured as objective / result / conclusion. Every save appends
an immutable WorkingPaperVersion snapshot so the full edit history stays
viewable; the audit trail also records each write.

Auditors are first-class preparers (create/edit/status), while deleting a
working paper needs Manager and above. Writes are blocked once the engagement
is completed.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, User, WorkingPaper, WorkingPaperVersion
from models.engagements_models import EngagementStatus
from models.working_papers_models import (
    WorkingPaperCreate,
    WorkingPaperRecord,
    WorkingPaperStatusUpdate,
    WorkingPaperUpdate,
    WorkingPaperVersionRecord,
)
from services import audit_trail_service
from utils.naming import display_name

ENTITY_TYPE = "working_paper"


async def _names_for(session: AsyncSession, ids: set[str]) -> dict[str, str]:
    """Resolve Clerk user ids to display names via the local user mirror so the
    UI shows people, not opaque ids (same approach as the audit trail)."""
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    users = list(await session.scalars(select(User).where(User.clerk_user_id.in_(wanted))))
    return {
        u.clerk_user_id: (display_name(u.first_name, u.last_name, u.email) or u.clerk_user_id)
        for u in users
        if u.clerk_user_id in wanted
    }


def _snapshot(wp: WorkingPaper) -> dict:
    return {
        "engagement_id": str(wp.engagement_id),
        "fs_area": wp.fs_area,
        "index_ref": wp.index_ref,
        "title": wp.title,
        "objective": wp.objective,
        "result": wp.result,
        "conclusion": wp.conclusion,
        "status": wp.status,
        "procedure_id": str(wp.procedure_id) if wp.procedure_id else None,
    }


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


def _require_not_completed(engagement: Engagement) -> None:
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify working papers of a completed engagement",
        )


async def _get_working_paper(
    session: AsyncSession, engagement_id: uuid.UUID, wp_id: uuid.UUID
) -> WorkingPaper:
    wp = (await session.scalars(select(WorkingPaper).where(WorkingPaper.id == wp_id))).first()
    if wp is None or wp.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working paper not found")
    return wp


async def _versions_for(session: AsyncSession, wp_id: uuid.UUID) -> list[WorkingPaperVersion]:
    rows = await session.scalars(
        select(WorkingPaperVersion).where(WorkingPaperVersion.working_paper_id == wp_id)
    )
    return [v for v in rows if v.working_paper_id == wp_id]


async def _max_versions(session: AsyncSession, wp_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not wp_ids:
        return {}
    rows = await session.scalars(
        select(WorkingPaperVersion).where(WorkingPaperVersion.working_paper_id.in_(wp_ids))
    )
    highest: dict[uuid.UUID, int] = {}
    for row in rows:
        if row.version_no > highest.get(row.working_paper_id, 0):
            highest[row.working_paper_id] = row.version_no
    return highest


def _append_version(
    session: AsyncSession, wp: WorkingPaper, *, version_no: int, editor: str
) -> None:
    session.add(
        WorkingPaperVersion(
            id=uuid.uuid4(),
            working_paper_id=wp.id,
            version_no=version_no,
            index_ref=wp.index_ref,
            fs_area=wp.fs_area,
            title=wp.title,
            objective=wp.objective,
            result=wp.result,
            conclusion=wp.conclusion,
            status=wp.status,
            edited_by=editor,
        )
    )


def _record(wp: WorkingPaper, current_version: int) -> WorkingPaperRecord:
    record = WorkingPaperRecord.model_validate(wp)
    record.current_version = current_version
    return record


async def _record_with_name(
    session: AsyncSession, wp: WorkingPaper, current_version: int
) -> WorkingPaperRecord:
    record = _record(wp, current_version)
    if wp.prepared_by:
        names = await _names_for(session, {wp.prepared_by})
        record.prepared_by_name = names.get(wp.prepared_by)
    return record


async def _require_unique_index(
    session: AsyncSession, engagement_id: uuid.UUID, index_ref: str, *, exclude: uuid.UUID | None
) -> None:
    existing = await session.scalars(
        select(WorkingPaper).where(WorkingPaper.engagement_id == engagement_id)
    )
    for wp in existing:
        if wp.engagement_id == engagement_id and wp.index_ref == index_ref and wp.id != exclude:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Index reference '{index_ref}' is already used on this engagement",
            )


async def list_working_papers(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    fs_area: str | None = None,
    wp_status: str | None = None,
) -> list[WorkingPaperRecord]:
    await _get_engagement(session, engagement_id)
    query = (
        select(WorkingPaper)
        .where(WorkingPaper.engagement_id == engagement_id)
        .order_by(WorkingPaper.fs_area, WorkingPaper.index_ref)
    )
    if fs_area:
        query = query.where(WorkingPaper.fs_area == fs_area)
    if wp_status:
        query = query.where(WorkingPaper.status == wp_status)
    rows = list(await session.scalars(query))
    versions = await _max_versions(session, [row.id for row in rows])
    names = await _names_for(session, {row.prepared_by for row in rows if row.prepared_by})
    records = []
    for row in rows:
        record = _record(row, versions.get(row.id, 0))
        if row.prepared_by:
            record.prepared_by_name = names.get(row.prepared_by)
        records.append(record)
    return records


async def get_working_paper(
    session: AsyncSession, engagement_id: uuid.UUID, wp_id: uuid.UUID
) -> WorkingPaperRecord:
    wp = await _get_working_paper(session, engagement_id, wp_id)
    versions = await _max_versions(session, [wp.id])
    return await _record_with_name(session, wp, versions.get(wp.id, 0))


async def create_working_paper(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    payload: WorkingPaperCreate,
) -> WorkingPaperRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    await _require_unique_index(session, engagement_id, payload.index_ref, exclude=None)

    wp = WorkingPaper(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        fs_area=str(payload.fs_area),
        index_ref=payload.index_ref,
        title=payload.title,
        objective=payload.objective,
        result=payload.result,
        conclusion=payload.conclusion,
        status="draft",
        procedure_id=payload.procedure_id,
        created_by=actor,
    )
    session.add(wp)
    _append_version(session, wp, version_no=1, editor=actor)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(wp.id),
        after=_snapshot(wp),
    )
    await session.commit()
    await session.refresh(wp)
    return await _record_with_name(session, wp, 1)


async def update_working_paper(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    wp_id: uuid.UUID,
    payload: WorkingPaperUpdate,
) -> WorkingPaperRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    wp = await _get_working_paper(session, engagement_id, wp_id)

    before = _snapshot(wp)
    updates = payload.model_dump(exclude_unset=True)
    if "fs_area" in updates and updates["fs_area"] is not None:
        updates["fs_area"] = str(updates["fs_area"])
    if "index_ref" in updates and updates["index_ref"] is not None:
        await _require_unique_index(session, engagement_id, updates["index_ref"], exclude=wp.id)
    for field, value in updates.items():
        setattr(wp, field, value)

    next_version = max((await _max_versions(session, [wp.id])).get(wp.id, 0) + 1, 1)
    _append_version(session, wp, version_no=next_version, editor=actor)
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(wp_id),
        before=before,
        after=_snapshot(wp),
    )
    await session.commit()
    await session.refresh(wp)
    return await _record_with_name(session, wp, next_version)


async def update_status(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    wp_id: uuid.UUID,
    payload: WorkingPaperStatusUpdate,
) -> WorkingPaperRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    wp = await _get_working_paper(session, engagement_id, wp_id)

    before = _snapshot(wp)
    wp.status = str(payload.status)
    if payload.status == "prepared":
        wp.prepared_by = actor
        wp.prepared_at = datetime.now(UTC)
    else:
        wp.prepared_by = None
        wp.prepared_at = None

    next_version = max((await _max_versions(session, [wp.id])).get(wp.id, 0) + 1, 1)
    _append_version(session, wp, version_no=next_version, editor=actor)
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(wp_id),
        before=before,
        after=_snapshot(wp),
    )
    await session.commit()
    await session.refresh(wp)
    return await _record_with_name(session, wp, next_version)


async def delete_working_paper(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, wp_id: uuid.UUID
) -> None:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    wp = await _get_working_paper(session, engagement_id, wp_id)

    await session.delete(wp)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(wp_id),
        before=_snapshot(wp),
    )
    await session.commit()


async def list_versions(
    session: AsyncSession, engagement_id: uuid.UUID, wp_id: uuid.UUID
) -> list[WorkingPaperVersionRecord]:
    await _get_working_paper(session, engagement_id, wp_id)
    versions = sorted(await _versions_for(session, wp_id), key=lambda v: v.version_no)
    names = await _names_for(session, {v.edited_by for v in versions})
    records = []
    for v in versions:
        record = WorkingPaperVersionRecord.model_validate(v)
        record.edited_by_name = names.get(v.edited_by)
        records.append(record)
    return records
