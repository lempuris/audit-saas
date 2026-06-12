"""Materiality per ISA 320: benchmark selection, overall + performance
materiality and the clearly-trivial threshold, with Partner/Admin approval
that locks the assessment.

One assessment per engagement, upserted while in draft. Amounts are computed
here from the benchmark amount and percentages and stored on the row, so an
approved assessment is a fixed record of what was approved. Approval locks
the row; a Partner/Admin can reopen it, which returns it to draft (audited).
"""

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, MaterialityAssessment
from models.engagements_models import EngagementStatus
from models.materiality_models import (
    MaterialityInput,
    MaterialityRecord,
    MaterialityStatus,
)
from services import audit_trail_service

ENTITY_TYPE = "materiality_assessment"

_CENT = Decimal("0.01")


def _amount(base: Decimal, percentage: Decimal) -> Decimal:
    return (base * percentage / Decimal(100)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _snapshot(assessment: MaterialityAssessment) -> dict:
    return {
        "engagement_id": str(assessment.engagement_id),
        "benchmark": assessment.benchmark,
        "benchmark_amount": str(assessment.benchmark_amount),
        "overall_percentage": str(assessment.overall_percentage),
        "overall_materiality": str(assessment.overall_materiality),
        "performance_percentage": str(assessment.performance_percentage),
        "performance_materiality": str(assessment.performance_materiality),
        "clearly_trivial_percentage": str(assessment.clearly_trivial_percentage),
        "clearly_trivial_threshold": str(assessment.clearly_trivial_threshold),
        "rationale": assessment.rationale,
        "status": assessment.status,
        "approved_by": assessment.approved_by,
    }


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _find(session: AsyncSession, engagement_id: uuid.UUID) -> MaterialityAssessment | None:
    return (
        await session.scalars(
            select(MaterialityAssessment).where(
                MaterialityAssessment.engagement_id == engagement_id
            )
        )
    ).first()


async def get_materiality(session: AsyncSession, engagement_id: uuid.UUID) -> MaterialityRecord:
    await _get_engagement(session, engagement_id)
    assessment = await _find(session, engagement_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No materiality assessment for this engagement",
        )
    return MaterialityRecord.model_validate(assessment)


async def upsert_materiality(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: MaterialityInput
) -> MaterialityRecord:
    engagement = await _get_engagement(session, engagement_id)
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot set materiality on a completed engagement",
        )

    assessment = await _find(session, engagement_id)
    if assessment is not None and assessment.status == MaterialityStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Materiality is approved and locked; reopen it before editing",
        )

    overall = _amount(payload.benchmark_amount, payload.overall_percentage)
    performance = _amount(overall, payload.performance_percentage)
    clearly_trivial = _amount(overall, payload.clearly_trivial_percentage)

    if assessment is None:
        assessment = MaterialityAssessment(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            benchmark=payload.benchmark,
            benchmark_amount=payload.benchmark_amount,
            overall_percentage=payload.overall_percentage,
            overall_materiality=overall,
            performance_percentage=payload.performance_percentage,
            performance_materiality=performance,
            clearly_trivial_percentage=payload.clearly_trivial_percentage,
            clearly_trivial_threshold=clearly_trivial,
            rationale=payload.rationale,
            status=MaterialityStatus.DRAFT,
        )
        session.add(assessment)
        audit_trail_service.record(
            session,
            actor=actor,
            action="create",
            entity_type=ENTITY_TYPE,
            entity_id=str(assessment.id),
            after=_snapshot(assessment),
        )
    else:
        before = _snapshot(assessment)
        assessment.benchmark = payload.benchmark
        assessment.benchmark_amount = payload.benchmark_amount
        assessment.overall_percentage = payload.overall_percentage
        assessment.overall_materiality = overall
        assessment.performance_percentage = payload.performance_percentage
        assessment.performance_materiality = performance
        assessment.clearly_trivial_percentage = payload.clearly_trivial_percentage
        assessment.clearly_trivial_threshold = clearly_trivial
        assessment.rationale = payload.rationale
        audit_trail_service.record(
            session,
            actor=actor,
            action="update",
            entity_type=ENTITY_TYPE,
            entity_id=str(assessment.id),
            before=before,
            after=_snapshot(assessment),
        )

    await session.commit()
    await session.refresh(assessment)
    return MaterialityRecord.model_validate(assessment)


async def approve(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID
) -> MaterialityRecord:
    await _get_engagement(session, engagement_id)
    assessment = await _find(session, engagement_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No materiality assessment for this engagement",
        )
    if assessment.status == MaterialityStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Materiality is already approved"
        )

    before = _snapshot(assessment)
    assessment.status = MaterialityStatus.APPROVED
    assessment.approved_by = actor
    assessment.approved_at = datetime.now(UTC)
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(assessment.id),
        before=before,
        after=_snapshot(assessment),
    )
    await session.commit()
    await session.refresh(assessment)
    return MaterialityRecord.model_validate(assessment)


async def reopen(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID
) -> MaterialityRecord:
    engagement = await _get_engagement(session, engagement_id)
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reopen materiality on a completed engagement",
        )
    assessment = await _find(session, engagement_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No materiality assessment for this engagement",
        )
    if assessment.status != MaterialityStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Materiality is not approved"
        )

    before = _snapshot(assessment)
    assessment.status = MaterialityStatus.DRAFT
    assessment.approved_by = None
    assessment.approved_at = None
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(assessment.id),
        before=before,
        after=_snapshot(assessment),
    )
    await session.commit()
    await session.refresh(assessment)
    return MaterialityRecord.model_validate(assessment)
