"""Cross-references (ISA 230): explicit, clickable links between an
engagement's working papers, trial-balance lines, and documents. Both ends are
validated to exist and belong to the engagement, and each end is resolved to a
human-readable label for display.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CrossReference,
    Document,
    Engagement,
    TrialBalance,
    TrialBalanceLine,
    WorkingPaper,
)
from models.cross_references_models import CrossReferenceCreate, CrossReferenceRecord
from services import audit_trail_service

ENTITY_TYPE = "cross_reference"


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _label_maps(
    session: AsyncSession, engagement_id: uuid.UUID
) -> dict[str, dict[uuid.UUID, str]]:
    """Build id→label lookups per artifact type for the engagement."""
    wps = {
        wp.id: f"{wp.index_ref} {wp.title}"
        for wp in await session.scalars(
            select(WorkingPaper).where(WorkingPaper.engagement_id == engagement_id)
        )
        if wp.engagement_id == engagement_id
    }
    docs = {
        d.id: d.filename
        for d in await session.scalars(
            select(Document).where(Document.engagement_id == engagement_id)
        )
        if d.engagement_id == engagement_id
    }
    tb = (
        await session.scalars(
            select(TrialBalance).where(TrialBalance.engagement_id == engagement_id)
        )
    ).first()
    lines: dict[uuid.UUID, str] = {}
    if tb is not None and tb.engagement_id == engagement_id:
        lines = {
            line.id: f"{line.account_code} {line.account_name}"
            for line in await session.scalars(
                select(TrialBalanceLine).where(TrialBalanceLine.trial_balance_id == tb.id)
            )
            if line.trial_balance_id == tb.id
        }
    return {"working_paper": wps, "trial_balance_line": lines, "document": docs}


def _label(maps: dict[str, dict[uuid.UUID, str]], ref_type: str, ref_id: uuid.UUID) -> str | None:
    return maps.get(ref_type, {}).get(ref_id)


def _record(ref: CrossReference, maps: dict[str, dict[uuid.UUID, str]]) -> CrossReferenceRecord:
    record = CrossReferenceRecord.model_validate(ref)
    record.source_label = _label(maps, ref.source_type, ref.source_id) or "(removed)"
    record.target_label = _label(maps, ref.target_type, ref.target_id) or "(removed)"
    return record


async def list_cross_references(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
) -> list[CrossReferenceRecord]:
    await _get_engagement(session, engagement_id)
    query = select(CrossReference).where(CrossReference.engagement_id == engagement_id)
    rows = [r for r in await session.scalars(query) if r.engagement_id == engagement_id]
    if source_type is not None:
        rows = [r for r in rows if r.source_type == source_type]
    if source_id is not None:
        rows = [r for r in rows if r.source_id == source_id]
    maps = await _label_maps(session, engagement_id)
    return [_record(r, maps) for r in rows]


async def create_cross_reference(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: CrossReferenceCreate
) -> CrossReferenceRecord:
    await _get_engagement(session, engagement_id)
    maps = await _label_maps(session, engagement_id)

    if _label(maps, str(payload.source_type), payload.source_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source item not found on this engagement",
        )
    if _label(maps, str(payload.target_type), payload.target_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target item not found on this engagement",
        )

    existing = [r for r in await session.scalars(select(CrossReference))]
    for r in existing:
        if (
            r.engagement_id == engagement_id
            and r.source_type == str(payload.source_type)
            and r.source_id == payload.source_id
            and r.target_type == str(payload.target_type)
            and r.target_id == payload.target_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="This cross-reference already exists"
            )

    ref = CrossReference(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        source_type=str(payload.source_type),
        source_id=payload.source_id,
        target_type=str(payload.target_type),
        target_id=payload.target_id,
        label=payload.label,
        created_by=actor,
    )
    session.add(ref)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(ref.id),
        after={
            "source_type": ref.source_type,
            "source_id": str(ref.source_id),
            "target_type": ref.target_type,
            "target_id": str(ref.target_id),
        },
    )
    await session.commit()
    await session.refresh(ref)
    return _record(ref, maps)


async def delete_cross_reference(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, reference_id: uuid.UUID
) -> None:
    await _get_engagement(session, engagement_id)
    ref = (
        await session.scalars(select(CrossReference).where(CrossReference.id == reference_id))
    ).first()
    if ref is None or ref.engagement_id != engagement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cross-reference not found"
        )
    await session.delete(ref)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(reference_id),
        before={
            "source_type": ref.source_type,
            "source_id": str(ref.source_id),
            "target_type": ref.target_type,
            "target_id": str(ref.target_id),
        },
    )
    await session.commit()
