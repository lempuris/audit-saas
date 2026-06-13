import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.sampling_models import SampleComputation, SampleCreate, SampleRecord
from services import sampling_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/samples", tags=["sampling"])

AnyStaff = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/preview", response_model=SampleComputation)
async def preview_sample(
    engagement_id: uuid.UUID, body: SampleCreate, _user: AnyStaff, db: Db
) -> SampleComputation:
    return await sampling_service.preview(db, engagement_id=engagement_id, payload=body)


@router.get("", response_model=list[SampleRecord])
async def list_samples(engagement_id: uuid.UUID, _user: AnyStaff, db: Db) -> list[SampleRecord]:
    return await sampling_service.list_samples(db, engagement_id)


@router.get("/{sample_id}", response_model=SampleRecord)
async def get_sample(
    engagement_id: uuid.UUID, sample_id: uuid.UUID, _user: AnyStaff, db: Db
) -> SampleRecord:
    return await sampling_service.get_sample(db, engagement_id, sample_id)


@router.post("", response_model=SampleRecord, status_code=201)
async def create_sample(
    engagement_id: uuid.UUID, body: SampleCreate, user: AnyStaff, db: Db
) -> SampleRecord:
    return await sampling_service.create_sample(
        db, actor=user.user_id, engagement_id=engagement_id, payload=body
    )


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    engagement_id: uuid.UUID, sample_id: uuid.UUID, user: AnyStaff, db: Db
) -> None:
    await sampling_service.delete_sample(
        db, actor=user.user_id, engagement_id=engagement_id, sample_id=sample_id
    )
