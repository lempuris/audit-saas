"""Audit programs per ISA 300/330: a firm-wide library of ISA-referenced
procedure templates, tailored into per-engagement programs where procedures
are assigned, given due dates, tracked by status and linked to the risks
they respond to.

Engagement procedures copy template fields at add time (template_id keeps
provenance) so template edits never rewrite an existing program. Status can
be moved by any role — but an Auditor only on procedures assigned to them —
while tailoring (add/edit/delete/assign/link) needs Manager and above.
"""

import uuid
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Engagement,
    EngagementProcedure,
    ProcedureTemplate,
    Risk,
    RiskProcedureLink,
)
from models.audit_programs_models import (
    ProcedureCreate,
    ProcedureRecord,
    ProceduresFromTemplates,
    ProcedureStatusUpdate,
    ProcedureUpdate,
    RiskLinksUpdate,
    SeedResult,
    TemplateCreate,
    TemplateRecord,
)
from models.auth_models import AuthenticatedUser, Role
from models.engagements_models import EngagementStatus
from services import audit_trail_service
from services.procedure_template_seed import SEED_TEMPLATES

ENTITY_TYPE = "engagement_procedure"
TEMPLATE_ENTITY_TYPE = "procedure_template"


def _template_snapshot(template: ProcedureTemplate) -> dict:
    return {
        "fs_area": template.fs_area,
        "title": template.title,
        "description": template.description,
        "isa_reference": template.isa_reference,
        "assertions": template.assertions,
        "sort_order": template.sort_order,
    }


def _snapshot(procedure: EngagementProcedure) -> dict:
    return {
        "engagement_id": str(procedure.engagement_id),
        "template_id": str(procedure.template_id) if procedure.template_id else None,
        "fs_area": procedure.fs_area,
        "title": procedure.title,
        "description": procedure.description,
        "isa_reference": procedure.isa_reference,
        "assertions": procedure.assertions,
        "assigned_to": procedure.assigned_to,
        "status": procedure.status,
        "due_date": procedure.due_date.isoformat() if procedure.due_date else None,
        "sort_order": procedure.sort_order,
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
            detail="Cannot modify the audit program of a completed engagement",
        )


async def _get_procedure(
    session: AsyncSession, engagement_id: uuid.UUID, procedure_id: uuid.UUID
) -> EngagementProcedure:
    procedure = (
        await session.scalars(
            select(EngagementProcedure).where(EngagementProcedure.id == procedure_id)
        )
    ).first()
    if procedure is None or procedure.engagement_id != engagement_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")
    return procedure


async def _links_by_procedure(
    session: AsyncSession, procedure_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not procedure_ids:
        return {}
    rows = await session.scalars(
        select(RiskProcedureLink).where(RiskProcedureLink.procedure_id.in_(procedure_ids))
    )
    links: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for row in rows:
        links[row.procedure_id].append(row.risk_id)
    return links


def _record(
    procedure: EngagementProcedure, linked_risk_ids: list[uuid.UUID] | None = None
) -> ProcedureRecord:
    record = ProcedureRecord.model_validate(procedure)
    record.linked_risk_ids = linked_risk_ids or []
    return record


# --- Templates (firm-wide library) ---


async def list_templates(
    session: AsyncSession, *, fs_area: str | None = None
) -> list[TemplateRecord]:
    query = select(ProcedureTemplate).order_by(
        ProcedureTemplate.fs_area, ProcedureTemplate.sort_order
    )
    if fs_area:
        query = query.where(ProcedureTemplate.fs_area == fs_area)
    rows = await session.scalars(query)
    return [TemplateRecord.model_validate(row) for row in rows]


async def create_template(
    session: AsyncSession, *, actor: str, payload: TemplateCreate
) -> TemplateRecord:
    existing = await session.scalars(select(ProcedureTemplate))
    if any(t.fs_area == payload.fs_area and t.title == payload.title for t in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with this title already exists for this FS area",
        )
    template = ProcedureTemplate(
        id=uuid.uuid4(),
        fs_area=payload.fs_area,
        title=payload.title,
        description=payload.description,
        isa_reference=payload.isa_reference,
        assertions=[str(a) for a in payload.assertions],
        sort_order=payload.sort_order,
    )
    session.add(template)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=TEMPLATE_ENTITY_TYPE,
        entity_id=str(template.id),
        after=_template_snapshot(template),
    )
    await session.commit()
    await session.refresh(template)
    return TemplateRecord.model_validate(template)


async def seed_templates(session: AsyncSession, *, actor: str) -> SeedResult:
    """Insert built-in templates that aren't already present (matched on
    fs_area + title), so re-seeding after firm additions is safe."""
    existing = {(t.fs_area, t.title) for t in await session.scalars(select(ProcedureTemplate))}
    created = 0
    for entry in SEED_TEMPLATES:
        if (entry["fs_area"], entry["title"]) in existing:
            continue
        session.add(ProcedureTemplate(id=uuid.uuid4(), **entry))
        created += 1
    if created:
        audit_trail_service.record(
            session,
            actor=actor,
            action="create",
            entity_type=TEMPLATE_ENTITY_TYPE,
            entity_id="seed",
            after={"created": created},
        )
        await session.commit()
    return SeedResult(created=created, skipped=len(SEED_TEMPLATES) - created)


# --- Engagement procedures ---


async def list_procedures(
    session: AsyncSession,
    engagement_id: uuid.UUID,
    *,
    fs_area: str | None = None,
    assigned_to: str | None = None,
    procedure_status: str | None = None,
) -> list[ProcedureRecord]:
    await _get_engagement(session, engagement_id)
    query = (
        select(EngagementProcedure)
        .where(EngagementProcedure.engagement_id == engagement_id)
        .order_by(EngagementProcedure.fs_area, EngagementProcedure.sort_order)
    )
    if fs_area:
        query = query.where(EngagementProcedure.fs_area == fs_area)
    if assigned_to:
        query = query.where(EngagementProcedure.assigned_to == assigned_to)
    if procedure_status:
        query = query.where(EngagementProcedure.status == procedure_status)
    rows = list(await session.scalars(query))
    links = await _links_by_procedure(session, [row.id for row in rows])
    return [_record(row, links.get(row.id)) for row in rows]


async def add_procedure(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, payload: ProcedureCreate
) -> ProcedureRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)

    template = None
    if payload.template_id is not None:
        template = (
            await session.scalars(
                select(ProcedureTemplate).where(ProcedureTemplate.id == payload.template_id)
            )
        ).first()
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    assertions = payload.assertions
    if assertions is None:
        assertions = template.assertions if template else []
    procedure = EngagementProcedure(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        template_id=payload.template_id,
        fs_area=payload.fs_area or (template.fs_area if template else None),
        title=payload.title or (template.title if template else None),
        description=payload.description or (template.description if template else None),
        isa_reference=payload.isa_reference or (template.isa_reference if template else None),
        assertions=[str(a) for a in assertions],
        status="not_started",
        sort_order=(
            payload.sort_order
            if payload.sort_order is not None
            else (template.sort_order if template else 0)
        ),
        created_by=actor,
    )
    session.add(procedure)
    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(procedure.id),
        after=_snapshot(procedure),
    )
    await session.commit()
    await session.refresh(procedure)
    return _record(procedure)


async def add_from_templates(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    payload: ProceduresFromTemplates,
) -> list[ProcedureRecord]:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)

    templates = list(await session.scalars(select(ProcedureTemplate)))
    if payload.template_ids is not None:
        by_id = {t.id: t for t in templates}
        missing = [str(i) for i in payload.template_ids if i not in by_id]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Templates not found: " + ", ".join(missing),
            )
        templates = [by_id[i] for i in payload.template_ids]
    elif payload.fs_area is not None:
        templates = [t for t in templates if t.fs_area == payload.fs_area]

    existing = await session.scalars(
        select(EngagementProcedure).where(EngagementProcedure.engagement_id == engagement_id)
    )
    already_added = {p.template_id for p in existing if p.template_id}

    created: list[EngagementProcedure] = []
    for template in templates:
        if template.id in already_added:
            continue
        procedure = EngagementProcedure(
            id=uuid.uuid4(),
            engagement_id=engagement_id,
            template_id=template.id,
            fs_area=template.fs_area,
            title=template.title,
            description=template.description,
            isa_reference=template.isa_reference,
            assertions=list(template.assertions),
            status="not_started",
            sort_order=template.sort_order,
            created_by=actor,
        )
        session.add(procedure)
        audit_trail_service.record(
            session,
            actor=actor,
            action="create",
            entity_type=ENTITY_TYPE,
            entity_id=str(procedure.id),
            after=_snapshot(procedure),
        )
        created.append(procedure)

    await session.commit()
    for procedure in created:
        await session.refresh(procedure)
    return [_record(procedure) for procedure in created]


async def update_procedure(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    procedure_id: uuid.UUID,
    payload: ProcedureUpdate,
) -> ProcedureRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    procedure = await _get_procedure(session, engagement_id, procedure_id)

    before = _snapshot(procedure)
    updates = payload.model_dump(exclude_unset=True)
    if "assertions" in updates and updates["assertions"] is not None:
        updates["assertions"] = [str(a) for a in updates["assertions"]]
    for field, value in updates.items():
        setattr(procedure, field, value)

    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(procedure_id),
        before=before,
        after=_snapshot(procedure),
    )
    await session.commit()
    await session.refresh(procedure)
    links = await _links_by_procedure(session, [procedure.id])
    return _record(procedure, links.get(procedure.id))


async def update_status(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    engagement_id: uuid.UUID,
    procedure_id: uuid.UUID,
    payload: ProcedureStatusUpdate,
) -> ProcedureRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    procedure = await _get_procedure(session, engagement_id, procedure_id)

    if user.role == Role.AUDITOR and procedure.assigned_to != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors can only update the status of procedures assigned to them",
        )

    before = _snapshot(procedure)
    procedure.status = payload.status
    audit_trail_service.record(
        session,
        actor=user.user_id,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(procedure_id),
        before=before,
        after=_snapshot(procedure),
    )
    await session.commit()
    await session.refresh(procedure)
    links = await _links_by_procedure(session, [procedure.id])
    return _record(procedure, links.get(procedure.id))


async def delete_procedure(
    session: AsyncSession, *, actor: str, engagement_id: uuid.UUID, procedure_id: uuid.UUID
) -> None:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    procedure = await _get_procedure(session, engagement_id, procedure_id)

    await session.delete(procedure)
    audit_trail_service.record(
        session,
        actor=actor,
        action="delete",
        entity_type=ENTITY_TYPE,
        entity_id=str(procedure_id),
        before=_snapshot(procedure),
    )
    await session.commit()


async def set_risk_links(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    procedure_id: uuid.UUID,
    payload: RiskLinksUpdate,
) -> ProcedureRecord:
    engagement = await _get_engagement(session, engagement_id)
    _require_not_completed(engagement)
    procedure = await _get_procedure(session, engagement_id, procedure_id)

    risks = list(await session.scalars(select(Risk).where(Risk.engagement_id == engagement_id)))
    engagement_risk_ids = {risk.id for risk in risks if risk.engagement_id == engagement_id}
    target_ids = set(payload.risk_ids)
    unknown = target_ids - engagement_risk_ids
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risks not found on this engagement: "
            + ", ".join(str(i) for i in sorted(unknown, key=str)),
        )

    existing = [
        link
        for link in await session.scalars(
            select(RiskProcedureLink).where(RiskProcedureLink.procedure_id == procedure_id)
        )
        if link.procedure_id == procedure_id
    ]
    before_ids = {link.risk_id for link in existing}

    for link in existing:
        if link.risk_id not in target_ids:
            await session.delete(link)
    for risk_id in target_ids - before_ids:
        session.add(RiskProcedureLink(id=uuid.uuid4(), risk_id=risk_id, procedure_id=procedure_id))

    audit_trail_service.record(
        session,
        actor=actor,
        action="update",
        entity_type=ENTITY_TYPE,
        entity_id=str(procedure_id),
        before={"linked_risk_ids": sorted(str(i) for i in before_ids)},
        after={"linked_risk_ids": sorted(str(i) for i in target_ids)},
    )
    await session.commit()
    await session.refresh(procedure)
    return _record(procedure, sorted(target_ids, key=str))
