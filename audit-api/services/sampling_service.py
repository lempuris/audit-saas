"""Audit sampling (ISA 530). The sample size uses a monetary (MUS-style)
substantive model — n = population_value × reliability_factor /
(tolerable − expected) — which is a defensible baseline for all three selection
methods. Selection is reproducible: a random seed is stored alongside the
selected item indices (random/systematic) or monetary points (MUS).

Drawing a sample is fieldwork, open to all signed-in staff; creating/deleting is
blocked once the engagement is completed.
"""

import math
import random
import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, Sample, WorkingPaper
from models.engagements_models import EngagementStatus
from models.sampling_models import (
    RELIABILITY_FACTORS,
    SampleComputation,
    SampleCreate,
    SampleMethod,
    SampleRecord,
)
from services import audit_trail_service

ENTITY_TYPE = "sample"


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
            detail="Cannot modify samples of a completed engagement",
        )


def compute(payload: SampleCreate) -> SampleComputation:
    """Compute sample size and a reproducible selection for the payload."""
    factor = RELIABILITY_FACTORS[payload.confidence_level]
    denominator = payload.tolerable_misstatement - payload.expected_misstatement
    raw_size = payload.population_value * factor / denominator
    size = max(1, math.ceil(raw_size))

    seed = random.randrange(1_000_000_000)
    rng = random.Random(seed)
    basis: dict[str, Any] = {
        "method": str(payload.method),
        "confidence_level": payload.confidence_level,
        "reliability_factor": str(factor),
        "random_seed": seed,
    }

    if payload.method in (SampleMethod.RANDOM, SampleMethod.SYSTEMATIC):
        population_size = payload.population_size or 0
        size = min(size, population_size)
        if payload.method == SampleMethod.RANDOM:
            selected = sorted(rng.sample(range(1, population_size + 1), size))
        else:  # systematic
            step = max(1, population_size // size)
            start = rng.randint(1, step)
            selected = [
                start + index * step
                for index in range(size)
                if start + index * step <= population_size
            ]
            basis["step"] = step
            basis["random_start"] = start
        basis["selected_items"] = selected
        size = len(selected)
    else:  # monetary_unit
        interval = (payload.population_value / Decimal(size)).quantize(Decimal("0.01"))
        interval_units = max(1, int(interval))
        start = rng.randint(1, interval_units)
        points = [
            start + index * interval_units
            for index in range(size)
            if start + index * interval_units <= int(payload.population_value)
        ]
        basis["interval"] = str(interval)
        basis["random_start"] = start
        basis["selected_monetary_units"] = points
        size = len(points)

    return SampleComputation(
        method=str(payload.method),
        sample_size=size,
        reliability_factor=factor,
        selection_basis=basis,
    )


async def _validate_working_paper(
    session: AsyncSession, engagement_id: uuid.UUID, working_paper_id: uuid.UUID
) -> None:
    wp = (
        await session.scalars(select(WorkingPaper).where(WorkingPaper.id == working_paper_id))
    ).first()
    if wp is None or wp.engagement_id != engagement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Working paper not found on this engagement",
        )


async def preview(
    session: AsyncSession, *, engagement_id: uuid.UUID, payload: SampleCreate
) -> SampleComputation:
    await _get_engagement(session, engagement_id)
    return compute(payload)


async def list_samples(session: AsyncSession, engagement_id: uuid.UUID) -> list[SampleRecord]:
    await _get_engagement(session, engagement_id)
    rows = [
        r
        for r in await session.scalars(
            select(Sample).where(Sample.engagement_id == engagement_id).order_by(Sample.created_at)
        )
        if r.engagement_id == engagement_id
    ]
    return [SampleRecord.model_validate(r) for r in rows]


async def get_sample(
    session: AsyncSession, engagement_id: uuid.UUID, sample_id: uuid.UUID
) -> SampleRecord:
    sample = (await session.scalars(select(Sample).where(Sample.id == sample_id))).first()
    if sample is None or sample.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return SampleRecord.model_validate(sample)


async def create_sample(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: SampleCreate
) -> SampleRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    if payload.working_paper_id is not None:
        await _validate_working_paper(session, engagement_id, payload.working_paper_id)

    computation = compute(payload)
    sample = Sample(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        working_paper_id=payload.working_paper_id,
        fs_area=str(payload.fs_area) if payload.fs_area else None,
        population_description=payload.population_description,
        method=str(payload.method),
        population_size=payload.population_size,
        population_value=payload.population_value,
        tolerable_misstatement=payload.tolerable_misstatement,
        expected_misstatement=payload.expected_misstatement,
        confidence_level=payload.confidence_level,
        reliability_factor=computation.reliability_factor,
        sample_size=computation.sample_size,
        selection_basis=computation.selection_basis,
        created_by=actor,
    )
    session.add(sample)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(sample.id),
        after={
            "method": sample.method,
            "sample_size": sample.sample_size,
            "population_description": sample.population_description,
        },
    )
    await session.commit()
    await session.refresh(sample)
    return SampleRecord.model_validate(sample)


async def delete_sample(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, sample_id: uuid.UUID
) -> None:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    sample = (await session.scalars(select(Sample).where(Sample.id == sample_id))).first()
    if sample is None or sample.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    await session.delete(sample)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(sample_id),
        before={"method": sample.method, "sample_size": sample.sample_size},
    )
    await session.commit()
