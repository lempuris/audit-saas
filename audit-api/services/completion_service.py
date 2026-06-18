"""Completion checklist (ISA 220/700 file completion): an ISA-mapped list of
items each engagement resolves before it can close. The standard library is
seeded per engagement (idempotent by item_key). Resolving an item means marking
it complete or not_applicable.

The completion gate — assert_ready_to_complete — is called by
engagements_service when an engagement moves review -> completed: it blocks while
the checklist is empty, any item is open, or any review note is uncleared.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CompletionChecklistItem, Engagement, ReviewNote, User
from models.completion_models import (
    RESOLVED_STATUSES,
    ChecklistItemRecord,
    ChecklistItemStatus,
    ChecklistItemUpdate,
    CompletionReadiness,
)
from services import audit_trail_service
from utils.naming import display_name

ENTITY_TYPE = "completion_checklist_item"

# Standard ISA completion checklist. Seeded per engagement; extend here and a
# re-seed adds the new items without disturbing resolved ones.
STANDARD_ITEMS: list[dict[str, str]] = [
    {
        "item_key": "subsequent_events",
        "category": "Subsequent events",
        "title": "Review subsequent events through the date of the auditor's report",
        "isa_reference": "ISA 560",
    },
    {
        "item_key": "going_concern",
        "category": "Going concern",
        "title": "Conclude on the appropriateness of the going concern basis of accounting",
        "isa_reference": "ISA 570",
    },
    {
        "item_key": "written_representations",
        "category": "Written representations",
        "title": "Obtain written representations from management",
        "isa_reference": "ISA 580",
    },
    {
        "item_key": "uncorrected_misstatements",
        "category": "Misstatements",
        "title": "Evaluate the effect of uncorrected misstatements",
        "isa_reference": "ISA 450",
    },
    {
        "item_key": "opening_balances",
        "category": "Opening balances & comparatives",
        "title": "Verify opening balances and comparative information",
        "isa_reference": "ISA 510 / 710",
    },
    {
        "item_key": "related_parties",
        "category": "Related parties",
        "title": "Conclude on related party relationships and transactions",
        "isa_reference": "ISA 550",
    },
    {
        "item_key": "litigation_claims",
        "category": "Litigation & claims",
        "title": "Assess litigation and claims affecting the financial statements",
        "isa_reference": "ISA 501",
    },
    {
        "item_key": "final_analytical_review",
        "category": "Final analytical review",
        "title": "Perform an overall analytical review at completion",
        "isa_reference": "ISA 520",
    },
    {
        "item_key": "tcwg_communication",
        "category": "Governance communication",
        "title": "Communicate findings to those charged with governance",
        "isa_reference": "ISA 260",
    },
    {
        "item_key": "independence_reconfirmed",
        "category": "Independence",
        "title": "Reconfirm independence and compliance with relevant ethical requirements",
        "isa_reference": "ISA 220",
    },
    {
        "item_key": "documentation_assembled",
        "category": "File assembly",
        "title": "Assemble the final audit documentation",
        "isa_reference": "ISA 230",
    },
    {
        "item_key": "eqr_completed",
        "category": "Engagement quality review",
        "title": "Complete the engagement quality review where required",
        "isa_reference": "ISA 220 / ISQM 2",
    },
]


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _items(session: AsyncSession, engagement_id: uuid.UUID) -> list[CompletionChecklistItem]:
    rows = await session.scalars(
        select(CompletionChecklistItem)
        .where(CompletionChecklistItem.engagement_id == engagement_id)
        .order_by(CompletionChecklistItem.sort_order)
    )
    return [i for i in rows if i.engagement_id == engagement_id]


async def _uncleared_notes(session: AsyncSession, engagement_id: uuid.UUID) -> list[ReviewNote]:
    rows = await session.scalars(
        select(ReviewNote).where(ReviewNote.engagement_id == engagement_id)
    )
    return [n for n in rows if n.engagement_id == engagement_id and n.status != "cleared"]


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


async def _records(
    session: AsyncSession, items: list[CompletionChecklistItem]
) -> list[ChecklistItemRecord]:
    names = await _names_for(session, {i.resolved_by for i in items if i.resolved_by})
    records = []
    for item in items:
        record = ChecklistItemRecord.model_validate(item)
        if item.resolved_by:
            record.resolved_by_name = names.get(item.resolved_by)
        records.append(record)
    return records


async def list_items(session: AsyncSession, engagement_id: uuid.UUID) -> list[ChecklistItemRecord]:
    await _get_engagement(session, engagement_id)
    return await _records(session, await _items(session, engagement_id))


async def seed_standard(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID
) -> list[ChecklistItemRecord]:
    """Add any standard items the engagement is missing (idempotent)."""
    await _get_engagement(session, engagement_id)
    existing = {i.item_key for i in await _items(session, engagement_id)}
    added = 0
    for order, spec in enumerate(STANDARD_ITEMS):
        if spec["item_key"] in existing:
            continue
        session.add(
            CompletionChecklistItem(
                id=uuid.uuid4(),
                engagement_id=engagement_id,
                item_key=spec["item_key"],
                category=spec["category"],
                title=spec["title"],
                isa_reference=spec["isa_reference"],
                status=ChecklistItemStatus.OPEN,
                sort_order=order,
            )
        )
        added += 1
    if added:
        audit_trail_service.record(
            session,
            actor=actor,
            action="create",
            entity_type=ENTITY_TYPE,
            entity_id=str(engagement_id),
            after={"seeded_items": added},
        )
    await session.commit()
    return await list_items(session, engagement_id)


async def update_item(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ChecklistItemUpdate,
) -> ChecklistItemRecord:
    item = next((i for i in await _items(session, engagement_id) if i.id == item_id), None)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found"
        )

    before = {"status": item.status, "note": item.note}
    item.status = str(payload.status)
    item.note = payload.note
    if payload.status in RESOLVED_STATUSES:
        item.resolved_by = actor
        item.resolved_at = datetime.now(UTC)
    else:
        item.resolved_by = None
        item.resolved_at = None
    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(item_id),
        before=before,
        after={"status": item.status, "note": item.note},
    )
    await session.commit()
    await session.refresh(item)
    return (await _records(session, [item]))[0]


async def readiness(session: AsyncSession, engagement_id: uuid.UUID) -> CompletionReadiness:
    await _get_engagement(session, engagement_id)
    items = await _items(session, engagement_id)
    open_items = sum(1 for i in items if i.status == ChecklistItemStatus.OPEN)
    uncleared = len(await _uncleared_notes(session, engagement_id))
    ready = bool(items) and open_items == 0 and uncleared == 0
    return CompletionReadiness(
        ready=ready,
        total_items=len(items),
        open_items=open_items,
        uncleared_notes=uncleared,
    )


async def assert_ready_to_complete(session: AsyncSession, engagement_id: uuid.UUID) -> None:
    """Completion gate. Raises 409 if the engagement cannot close yet."""
    items = await _items(session, engagement_id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Initialize and complete the ISA completion checklist before closing",
        )
    open_items = sum(1 for i in items if i.status == ChecklistItemStatus.OPEN)
    if open_items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{open_items} completion checklist item(s) still open",
        )
    uncleared = len(await _uncleared_notes(session, engagement_id))
    if uncleared:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{uncleared} review note(s) still uncleared",
        )
