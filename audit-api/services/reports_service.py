"""Engagement reports (ISA 700/705/706): the audit report and the management
letter. A report is created from the standard ISA template library with editable
sections; the firm then tailors section bodies and the letterhead. One report of
each type per engagement.

Finalizing a report (status 'final') is restricted to Partner/Admin, and a
finalized report can only be changed by a Partner/Admin. PDF rendering is
feature 4.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, EngagementReport
from models.auth_models import Role
from models.reports_models import (
    ReportCreate,
    ReportRecord,
    ReportStatus,
    ReportType,
    ReportUpdate,
)
from services import audit_trail_service, engagement_lock, report_template_seed

ENTITY_TYPE = "engagement_report"


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _reports(session: AsyncSession, engagement_id: uuid.UUID) -> list[EngagementReport]:
    rows = await session.scalars(
        select(EngagementReport)
        .where(EngagementReport.engagement_id == engagement_id)
        .order_by(EngagementReport.report_type)
    )
    return [r for r in rows if r.engagement_id == engagement_id]


async def _get_report(
    session: AsyncSession, engagement_id: uuid.UUID, report_id: uuid.UUID
) -> EngagementReport:
    report = (
        await session.scalars(select(EngagementReport).where(EngagementReport.id == report_id))
    ).first()
    if report is None or report.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def _snapshot(report: EngagementReport) -> dict:
    return {
        "report_type": report.report_type,
        "opinion_type": report.opinion_type,
        "title": report.title,
        "status": report.status,
    }


async def list_reports(session: AsyncSession, engagement_id: uuid.UUID) -> list[ReportRecord]:
    await _get_engagement(session, engagement_id)
    return [ReportRecord.model_validate(r) for r in await _reports(session, engagement_id)]


async def get_report(
    session: AsyncSession, engagement_id: uuid.UUID, report_id: uuid.UUID
) -> ReportRecord:
    return ReportRecord.model_validate(await _get_report(session, engagement_id, report_id))


async def create_report(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: ReportCreate
) -> ReportRecord:
    engagement_lock.require_open(await _get_engagement(session, engagement_id))
    existing = await _reports(session, engagement_id)
    if any(r.report_type == str(payload.report_type) for r in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {payload.report_type} already exists for this engagement",
        )

    opinion = str(payload.opinion_type) if payload.opinion_type else None
    report = EngagementReport(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        report_type=str(payload.report_type),
        opinion_type=opinion,
        title=report_template_seed.default_title(str(payload.report_type)),
        letterhead=report_template_seed.DEFAULT_LETTERHEAD,
        sections=report_template_seed.standard_sections(str(payload.report_type), opinion),
        status=ReportStatus.DRAFT,
        created_by=actor,
    )
    session.add(report)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(report.id),
        after=_snapshot(report),
    )
    await session.commit()
    await session.refresh(report)
    return ReportRecord.model_validate(report)


async def update_report(
    session: AsyncSession,
    *,
    actor: str,
    actor_role: Role | None,
    engagement_id: uuid.UUID,
    report_id: uuid.UUID,
    payload: ReportUpdate,
) -> ReportRecord:
    engagement = await _get_engagement(session, engagement_id)
    report = await _get_report(session, engagement_id, report_id)
    is_partner = actor_role in (Role.PARTNER, Role.ADMIN)

    # An archived (completed) engagement is read-only, but a Partner/Admin may
    # still amend its reports (e.g. change the opinion): ISA 230 permits
    # post-assembly modifications provided they are documented, which the
    # audit-trail row below satisfies. Creating and deleting reports on an
    # archived file stay locked for everyone.
    if not is_partner:
        engagement_lock.require_open(engagement)

    # A finalized report is locked to Partner/Admin.
    if report.status == ReportStatus.FINAL and not is_partner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A finalized report can only be changed by a Partner or Admin",
        )
    # Finalizing an opinion is a Partner/Admin act.
    if payload.status == ReportStatus.FINAL and not is_partner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a Partner or Admin can finalize a report",
        )

    before = _snapshot(report)
    if payload.title is not None:
        report.title = payload.title
    if payload.letterhead is not None:
        report.letterhead = payload.letterhead
    if payload.status is not None:
        report.status = str(payload.status)
    if payload.sections is not None:
        report.sections = [s.model_dump() for s in payload.sections]

    # Changing the opinion type regenerates the opinion-driven sections (Opinion
    # + Basis for Opinion) — both heading and body — to the standard ISA
    # 700/705/706 wording for the new opinion, so the paragraph text matches the
    # chosen opinion. Other section edits are preserved. Opinion does not apply
    # to a management letter.
    new_opinion = str(payload.opinion_type) if payload.opinion_type else None
    if new_opinion is not None and new_opinion != report.opinion_type:
        if report.report_type == str(ReportType.MANAGEMENT_LETTER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="opinion_type does not apply to a management letter",
            )
        report.opinion_type = new_opinion
        refreshed = report_template_seed.opinion_sections(new_opinion)
        report.sections = [
            {**section, **refreshed[section["key"]]} if section["key"] in refreshed else section
            for section in report.sections
        ]

    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(report_id),
        before=before,
        after=_snapshot(report),
    )
    await session.commit()
    await session.refresh(report)
    return ReportRecord.model_validate(report)


async def delete_report(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, report_id: uuid.UUID
) -> None:
    engagement_lock.require_open(await _get_engagement(session, engagement_id))
    report = await _get_report(session, engagement_id, report_id)
    await session.delete(report)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(report_id),
        before=_snapshot(report),
    )
    await session.commit()
