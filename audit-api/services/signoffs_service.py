"""Sign-off workflow (ISA 220): working papers and FS areas advance
prepared -> reviewed -> approved. Reviewing needs Manager and above; approving
needs Partner/Admin. Every transition writes an immutable Signoff row (the
timestamped who/what/when) and an audit-trail row; the working paper's current
state is held on WorkingPaper.status, while an FS area's state is derived from
its Signoff rows. Returning a working paper sends it back to 'prepared' so the
preparer can edit it again.

Sign-offs are append-only: nothing here updates or deletes a Signoff row, so
the sign-off history is itself the audit record.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, Signoff, User, WorkingPaper
from models.auth_models import Role
from models.engagements_models import EngagementStatus
from models.signoffs_models import SignoffAction, SignoffRecord, SignoffRequest, SignoffTargetType
from services import audit_trail_service
from utils.naming import display_name

ENTITY_TYPE = "sign_off"

# Working-paper statuses, in workflow order.
WP_DRAFT = "draft"
WP_PREPARED = "prepared"
WP_REVIEWED = "reviewed"
WP_APPROVED = "approved"


async def _names_for(session: AsyncSession, ids: set[str]) -> dict[str, str]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    users = list(await session.scalars(select(User).where(User.clerk_user_id.in_(wanted))))
    return {
        u.clerk_user_id: (display_name(u.first_name, u.last_name, u.email) or u.clerk_user_id)
        for u in users
        if u.clerk_user_id in wanted
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
            detail="Cannot sign off on a completed engagement",
        )


async def _get_working_paper(
    session: AsyncSession, engagement_id: uuid.UUID, wp_id: uuid.UUID
) -> WorkingPaper:
    wp = (await session.scalars(select(WorkingPaper).where(WorkingPaper.id == wp_id))).first()
    if wp is None or wp.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working paper not found")
    return wp


async def _working_papers_in_area(
    session: AsyncSession, engagement_id: uuid.UUID, fs_area: str
) -> list[WorkingPaper]:
    rows = await session.scalars(
        select(WorkingPaper).where(WorkingPaper.engagement_id == engagement_id)
    )
    return [wp for wp in rows if wp.engagement_id == engagement_id and wp.fs_area == fs_area]


def _require_approver(action: SignoffAction, role: Role | None) -> None:
    if action == SignoffAction.APPROVE and role not in (Role.PARTNER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a Partner or Admin can approve",
        )


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


async def _record(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    target_type: SignoffTargetType,
    target_id: str,
    event: str,
    resulting_status: str,
    note: str | None,
) -> Signoff:
    signoff = Signoff(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        target_type=str(target_type),
        target_id=target_id,
        action=event,
        resulting_status=resulting_status,
        signed_by=actor,
        note=note,
    )
    session.add(signoff)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(signoff.id),
        after={
            "target_type": str(target_type),
            "target_id": target_id,
            "action": event,
            "resulting_status": resulting_status,
        },
    )
    return signoff


async def _to_record(session: AsyncSession, signoff: Signoff) -> SignoffRecord:
    record = SignoffRecord.model_validate(signoff)
    names = await _names_for(session, {signoff.signed_by})
    record.signed_by_name = names.get(signoff.signed_by)
    return record


async def sign_off_working_paper(
    session: AsyncSession,
    *,
    actor: str,
    actor_role: Role | None,
    engagement_id: uuid.UUID,
    wp_id: uuid.UUID,
    payload: SignoffRequest,
) -> SignoffRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    _require_approver(payload.action, actor_role)
    wp = await _get_working_paper(session, engagement_id, wp_id)

    if payload.action == SignoffAction.REVIEW:
        if wp.status != WP_PREPARED:
            raise _conflict("Working paper must be prepared before it can be reviewed")
        event, new_status = "reviewed", WP_REVIEWED
    elif payload.action == SignoffAction.APPROVE:
        if wp.status != WP_REVIEWED:
            raise _conflict("Working paper must be reviewed before it can be approved")
        event, new_status = "approved", WP_APPROVED
    else:  # RETURN
        if wp.status not in (WP_REVIEWED, WP_APPROVED):
            raise _conflict("Only a reviewed or approved working paper can be returned")
        event, new_status = "returned", WP_PREPARED

    wp.status = new_status
    signoff = await _record(
        session,
        actor=actor,
        engagement_id=engagement_id,
        target_type=SignoffTargetType.WORKING_PAPER,
        target_id=str(wp.id),
        event=event,
        resulting_status=new_status,
        note=payload.note,
    )
    await session.commit()
    await session.refresh(signoff)
    return await _to_record(session, signoff)


async def sign_off_fs_area(
    session: AsyncSession,
    *,
    actor: str,
    actor_role: Role | None,
    engagement_id: uuid.UUID,
    fs_area: str,
    payload: SignoffRequest,
) -> SignoffRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    _require_approver(payload.action, actor_role)

    if payload.action == SignoffAction.RETURN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return applies to individual working papers, not an FS area",
        )

    wps = await _working_papers_in_area(session, engagement_id, fs_area)
    if not wps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No working papers in this FS area to sign off",
        )

    if payload.action == SignoffAction.REVIEW:
        if not all(wp.status in (WP_REVIEWED, WP_APPROVED) for wp in wps):
            raise _conflict("Every working paper in the area must be reviewed first")
        event = "reviewed"
    else:  # APPROVE
        if not all(wp.status == WP_APPROVED for wp in wps):
            raise _conflict("Every working paper in the area must be approved first")
        event = "approved"

    signoff = await _record(
        session,
        actor=actor,
        engagement_id=engagement_id,
        target_type=SignoffTargetType.FS_AREA,
        target_id=fs_area,
        event=event,
        resulting_status=event,
        note=payload.note,
    )
    await session.commit()
    await session.refresh(signoff)
    return await _to_record(session, signoff)


async def list_sign_offs(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
) -> list[SignoffRecord]:
    await _get_engagement(session, engagement_id)
    rows = await session.scalars(
        select(Signoff).where(Signoff.engagement_id == engagement_id).order_by(Signoff.created_at)
    )
    signoffs = [
        s
        for s in rows
        if s.engagement_id == engagement_id
        and (target_type is None or s.target_type == target_type)
        and (target_id is None or s.target_id == target_id)
    ]
    names = await _names_for(session, {s.signed_by for s in signoffs})
    records = []
    for s in signoffs:
        record = SignoffRecord.model_validate(s)
        record.signed_by_name = names.get(s.signed_by)
        records.append(record)
    return records
