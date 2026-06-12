import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
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
from services import audit_programs_service

templates_router = APIRouter(prefix="/api/procedure-templates", tags=["audit-programs"])
router = APIRouter(prefix="/api/engagements/{engagement_id}/procedures", tags=["audit-programs"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


@templates_router.get("", response_model=list[TemplateRecord])
async def list_templates(_user: Reader, db: Db, fs_area: str | None = None) -> list[TemplateRecord]:
    return await audit_programs_service.list_templates(db, fs_area=fs_area)


@templates_router.post("", response_model=TemplateRecord, status_code=201)
async def create_template(body: TemplateCreate, user: Writer, db: Db) -> TemplateRecord:
    return await audit_programs_service.create_template(db, actor=user.user_id, payload=body)


@templates_router.post("/seed", response_model=SeedResult)
async def seed_templates(user: Writer, db: Db) -> SeedResult:
    return await audit_programs_service.seed_templates(db, actor=user.user_id)


@router.get("", response_model=list[ProcedureRecord])
async def list_procedures(
    engagement_id: uuid.UUID,
    _user: Reader,
    db: Db,
    fs_area: str | None = None,
    assigned_to: str | None = None,
    procedure_status: str | None = None,
) -> list[ProcedureRecord]:
    return await audit_programs_service.list_procedures(
        db,
        engagement_id,
        fs_area=fs_area,
        assigned_to=assigned_to,
        procedure_status=procedure_status,
    )


@router.post("", response_model=ProcedureRecord, status_code=201)
async def add_procedure(
    engagement_id: uuid.UUID, body: ProcedureCreate, user: Writer, db: Db
) -> ProcedureRecord:
    return await audit_programs_service.add_procedure(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.post("/from-templates", response_model=list[ProcedureRecord], status_code=201)
async def add_from_templates(
    engagement_id: uuid.UUID, body: ProceduresFromTemplates, user: Writer, db: Db
) -> list[ProcedureRecord]:
    return await audit_programs_service.add_from_templates(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.patch("/{procedure_id}", response_model=ProcedureRecord)
async def update_procedure(
    engagement_id: uuid.UUID, procedure_id: uuid.UUID, body: ProcedureUpdate, user: Writer, db: Db
) -> ProcedureRecord:
    return await audit_programs_service.update_procedure(
        db, actor=user.user_id, engagement_id=engagement_id, procedure_id=procedure_id, payload=body
    )


@router.patch("/{procedure_id}/status", response_model=ProcedureRecord)
async def update_status(
    engagement_id: uuid.UUID,
    procedure_id: uuid.UUID,
    body: ProcedureStatusUpdate,
    user: Reader,
    db: Db,
) -> ProcedureRecord:
    # Auditors may only move procedures assigned to them — enforced in the service.
    return await audit_programs_service.update_status(
        db, user=user, engagement_id=engagement_id, procedure_id=procedure_id, payload=body
    )


@router.put("/{procedure_id}/risks", response_model=ProcedureRecord)
async def set_risk_links(
    engagement_id: uuid.UUID, procedure_id: uuid.UUID, body: RiskLinksUpdate, user: Writer, db: Db
) -> ProcedureRecord:
    return await audit_programs_service.set_risk_links(
        db, actor=user.user_id, engagement_id=engagement_id, procedure_id=procedure_id, payload=body
    )


@router.delete("/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    engagement_id: uuid.UUID, procedure_id: uuid.UUID, user: Writer, db: Db
) -> None:
    await audit_programs_service.delete_procedure(
        db, actor=user.user_id, engagement_id=engagement_id, procedure_id=procedure_id
    )
