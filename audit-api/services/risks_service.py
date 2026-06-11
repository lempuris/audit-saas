"""Risk assessment per ISA 315: entity-level and assertion-level risks of
material misstatement, rated inherent x control with a derived combined
rating. Assertion-level risks target an FS area (and optionally specific
assertions) so they can drive the audit program for that area.

The combined rating comes from the standard two-factor matrix below — it is
stored on the row so listings don't recompute it, and recomputed whenever
either input rating changes.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, Risk
from models.engagements_models import EngagementStatus
from models.risks_models import RiskCreate, RiskRating, RiskRecord, RiskUpdate
from services import audit_trail_service

ENTITY_TYPE = "risk"

# (inherent, control) -> combined risk of material misstatement. Control
# rating reflects control RISK (high = controls cannot be relied on).
COMBINED_RATING: dict[tuple[str, str], str] = {
    (RiskRating.LOW, RiskRating.LOW): RiskRating.LOW,
    (RiskRating.LOW, RiskRating.MEDIUM): RiskRating.LOW,
    (RiskRating.LOW, RiskRating.HIGH): RiskRating.MEDIUM,
    (RiskRating.MEDIUM, RiskRating.LOW): RiskRating.LOW,
    (RiskRating.MEDIUM, RiskRating.MEDIUM): RiskRating.MEDIUM,
    (RiskRating.MEDIUM, RiskRating.HIGH): RiskRating.HIGH,
    (RiskRating.HIGH, RiskRating.LOW): RiskRating.MEDIUM,
    (RiskRating.HIGH, RiskRating.MEDIUM): RiskRating.HIGH,
    (RiskRating.HIGH, RiskRating.HIGH): RiskRating.HIGH,
}


def _snapshot(risk: Risk) -> dict:
    return {
        "engagement_id": str(risk.engagement_id),
        "level": risk.level,
        "fs_area": risk.fs_area,
        "assertions": risk.assertions,
        "description": risk.description,
        "inherent_rating": risk.inherent_rating,
        "control_rating": risk.control_rating,
        "combined_rating": risk.combined_rating,
        "is_significant": risk.is_significant,
        "planned_response": risk.planned_response,
    }


async def _get_open_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
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
            detail="Cannot modify risks on a completed engagement",
        )


async def _get_risk(session: AsyncSession, engagement_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = (await session.scalars(select(Risk).where(Risk.id == risk_id))).first()
    if risk is None or risk.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    return risk


async def list_risks(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    level: str | None = None,
    fs_area: str | None = None,
) -> list[RiskRecord]:
    await _get_open_engagement(session, engagement_id)
    query = select(Risk).where(Risk.engagement_id == engagement_id).order_by(Risk.created_at)
    if level:
        query = query.where(Risk.level == level)
    if fs_area:
        query = query.where(Risk.fs_area == fs_area)
    rows = await session.scalars(query)
    return [RiskRecord.model_validate(row) for row in rows]


async def get_risk(
    session: AsyncSession, engagement_id: uuid.UUID, risk_id: uuid.UUID
) -> RiskRecord:
    risk = await _get_risk(session, engagement_id, risk_id)
    return RiskRecord.model_validate(risk)


async def create_risk(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: RiskCreate
) -> RiskRecord:
    engagement = await _get_open_engagement(session, engagement_id)
    _require_not_completed(engagement)

    risk = Risk(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        level=payload.level,
        fs_area=payload.fs_area,
        assertions=[str(a) for a in payload.assertions],
        description=payload.description,
        inherent_rating=payload.inherent_rating,
        control_rating=payload.control_rating,
        combined_rating=COMBINED_RATING[(payload.inherent_rating, payload.control_rating)],
        is_significant=payload.is_significant,
        planned_response=payload.planned_response,
        created_by=actor,
    )
    session.add(risk)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(risk.id),
        after=_snapshot(risk),
    )
    await session.commit()
    await session.refresh(risk)
    return RiskRecord.model_validate(risk)


async def update_risk(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    risk_id: uuid.UUID,
    payload: RiskUpdate,
) -> RiskRecord:
    engagement = await _get_open_engagement(session, engagement_id)
    _require_not_completed(engagement)
    risk = await _get_risk(session, engagement_id, risk_id)

    before = _snapshot(risk)
    updates = payload.model_dump(exclude_unset=True)
    if "assertions" in updates and updates["assertions"] is not None:
        updates["assertions"] = [str(a) for a in updates["assertions"]]
    for field, value in updates.items():
        setattr(risk, field, value)
    if risk.level == "entity" and (risk.fs_area or risk.assertions):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Entity-level risks cannot target an FS area or assertions",
        )
    risk.combined_rating = COMBINED_RATING[(risk.inherent_rating, risk.control_rating)]

    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(risk_id),
        before=before,
        after=_snapshot(risk),
    )
    await session.commit()
    await session.refresh(risk)
    return RiskRecord.model_validate(risk)


async def delete_risk(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, risk_id: uuid.UUID
) -> None:
    engagement = await _get_open_engagement(session, engagement_id)
    _require_not_completed(engagement)
    risk = await _get_risk(session, engagement_id, risk_id)

    await session.delete(risk)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(risk_id),
        before=_snapshot(risk),
    )
    await session.commit()
