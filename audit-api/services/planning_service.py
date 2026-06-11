"""Planning views computed from data the other Phase 2 features own: lead
schedules generated per FS area from the imported trial balance, a planning
summary (dashboard) per engagement, and the caller's assigned procedures
across engagements. Read-only — nothing here writes, so no audit rows."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Client,
    Engagement,
    EngagementProcedure,
    MaterialityAssessment,
    Risk,
    TrialBalance,
    TrialBalanceLine,
)
from models.audit_programs_models import ProcedureStatus
from models.planning_models import (
    LeadSchedule,
    LeadScheduleLine,
    LeadScheduleSummary,
    MaterialityProgress,
    MyProcedure,
    PlanningSummary,
    ProcedureProgress,
    RiskProgress,
    TrialBalanceProgress,
)
from models.risks_models import RiskRating

# Plain strings, not enum members: Enum hashes by member name, so a set of
# StrEnum members never matches the plain status strings stored on rows.
OPEN_PROCEDURE_STATUSES = {str(ProcedureStatus.NOT_STARTED), str(ProcedureStatus.IN_PROGRESS)}


def _today() -> datetime:
    return datetime.now(UTC)


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _tb_lines(
    session: AsyncSession, engagement_id: uuid.UUID
) -> list[TrialBalanceLine] | None:
    """The engagement's TB lines, or None when no TB has been imported."""
    trial_balance = (
        await session.scalars(
            select(TrialBalance).where(TrialBalance.engagement_id == engagement_id)
        )
    ).first()
    if trial_balance is None:
        return None
    rows = await session.scalars(
        select(TrialBalanceLine).where(TrialBalanceLine.trial_balance_id == trial_balance.id)
    )
    return [line for line in rows if line.trial_balance_id == trial_balance.id]


def _movement(balance: Decimal, prior: Decimal | None) -> Decimal | None:
    return None if prior is None else balance - prior


def _schedule(fs_area: str, lines: list[TrialBalanceLine]) -> LeadSchedule:
    schedule_lines = [
        LeadScheduleLine(
            line_id=line.id,
            account_code=line.account_code,
            account_name=line.account_name,
            balance=line.balance,
            prior_year_balance=line.prior_year_balance,
            movement=_movement(line.balance, line.prior_year_balance),
        )
        for line in sorted(lines, key=lambda line: line.account_code)
    ]
    balance = sum((line.balance for line in lines), Decimal(0))
    priors = [line.prior_year_balance for line in lines]
    # Prior-year totals only make sense when every line carries one.
    prior_total = (
        sum((p for p in priors if p is not None), Decimal(0))
        if any(p is not None for p in priors)
        else None
    )
    return LeadSchedule(
        fs_area=fs_area,
        line_count=len(lines),
        balance=balance,
        prior_year_balance=prior_total,
        movement=_movement(balance, prior_total),
        lines=schedule_lines,
    )


async def list_lead_schedules(
    session: AsyncSession, engagement_id: uuid.UUID
) -> list[LeadScheduleSummary]:
    await _get_engagement(session, engagement_id)
    lines = await _tb_lines(session, engagement_id)
    if lines is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trial balance imported for this engagement",
        )
    by_area: dict[str, list[TrialBalanceLine]] = {}
    for line in lines:
        if line.fs_area:
            by_area.setdefault(line.fs_area, []).append(line)
    schedules = [_schedule(area, area_lines) for area, area_lines in by_area.items()]
    schedules.sort(key=lambda s: s.fs_area)
    return [LeadScheduleSummary(**s.model_dump(exclude={"lines"})) for s in schedules]


async def get_lead_schedule(
    session: AsyncSession, engagement_id: uuid.UUID, fs_area: str
) -> LeadSchedule:
    await _get_engagement(session, engagement_id)
    lines = await _tb_lines(session, engagement_id)
    if lines is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trial balance imported for this engagement",
        )
    area_lines = [line for line in lines if line.fs_area == fs_area]
    if not area_lines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trial balance lines grouped under '{fs_area}'",
        )
    return _schedule(fs_area, area_lines)


async def planning_summary(session: AsyncSession, engagement_id: uuid.UUID) -> PlanningSummary:
    engagement = await _get_engagement(session, engagement_id)

    lines = await _tb_lines(session, engagement_id)
    trial_balance = TrialBalanceProgress(
        imported=lines is not None,
        line_count=len(lines or []),
        unmapped_count=sum(1 for line in lines or [] if not line.fs_area),
    )

    assessment = (
        await session.scalars(
            select(MaterialityAssessment).where(
                MaterialityAssessment.engagement_id == engagement_id
            )
        )
    ).first()
    materiality = (
        MaterialityProgress(
            status=assessment.status,
            overall_materiality=assessment.overall_materiality,
            performance_materiality=assessment.performance_materiality,
            clearly_trivial_threshold=assessment.clearly_trivial_threshold,
        )
        if assessment
        else None
    )

    risks = [
        risk
        for risk in await session.scalars(select(Risk).where(Risk.engagement_id == engagement_id))
        if risk.engagement_id == engagement_id
    ]
    risk_progress = RiskProgress(
        total=len(risks),
        significant=sum(1 for risk in risks if risk.is_significant),
        entity_level=sum(1 for risk in risks if risk.level == "entity"),
        assertion_level=sum(1 for risk in risks if risk.level == "assertion"),
        by_combined_rating={
            str(rating): sum(1 for risk in risks if risk.combined_rating == rating)
            for rating in RiskRating
        },
    )

    procedures = [
        procedure
        for procedure in await session.scalars(
            select(EngagementProcedure).where(EngagementProcedure.engagement_id == engagement_id)
        )
        if procedure.engagement_id == engagement_id
    ]
    today = _today().date()
    procedure_progress = ProcedureProgress(
        total=len(procedures),
        by_status={
            str(s): sum(1 for procedure in procedures if procedure.status == s)
            for s in ProcedureStatus
        },
        overdue=sum(
            1
            for procedure in procedures
            if procedure.due_date
            and procedure.due_date < today
            and procedure.status in OPEN_PROCEDURE_STATUSES
        ),
        unassigned=sum(1 for procedure in procedures if not procedure.assigned_to),
    )

    return PlanningSummary(
        engagement_id=engagement_id,
        engagement_status=engagement.status,
        trial_balance=trial_balance,
        materiality=materiality,
        risks=risk_progress,
        procedures=procedure_progress,
    )


async def my_procedures(session: AsyncSession, *, user_id: str) -> list[MyProcedure]:
    procedures = [
        procedure
        for procedure in await session.scalars(
            select(EngagementProcedure).where(EngagementProcedure.assigned_to == user_id)
        )
        if procedure.assigned_to == user_id
    ]
    if not procedures:
        return []

    engagements = {
        engagement.id: engagement
        for engagement in await session.scalars(
            select(Engagement).where(
                Engagement.id.in_({procedure.engagement_id for procedure in procedures})
            )
        )
    }
    clients = {
        client.id: client
        for client in await session.scalars(
            select(Client).where(Client.id.in_({e.client_id for e in engagements.values()}))
        )
    }

    today = _today().date()
    results = []
    for procedure in procedures:
        engagement = engagements.get(procedure.engagement_id)
        if engagement is None:
            continue
        client = clients.get(engagement.client_id)
        results.append(
            MyProcedure(
                id=procedure.id,
                engagement_id=procedure.engagement_id,
                engagement_status=engagement.status,
                fiscal_year=engagement.fiscal_year,
                client_name=client.name if client else None,
                fs_area=procedure.fs_area,
                title=procedure.title,
                isa_reference=procedure.isa_reference,
                status=procedure.status,
                due_date=procedure.due_date,
                overdue=bool(
                    procedure.due_date
                    and procedure.due_date < today
                    and procedure.status in OPEN_PROCEDURE_STATUSES
                ),
            )
        )
    results.sort(key=lambda p: (p.due_date is None, p.due_date or today, p.title))
    return results
