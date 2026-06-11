import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from middleware.auth import require_roles
from models.auth_models import AuthenticatedUser, Role
from models.trial_balance_models import (
    ColumnMapping,
    FSAreaSummary,
    LineGroupingUpdate,
    TrialBalanceDetail,
    TrialBalanceLineRecord,
    TrialBalancePreview,
)
from services import trial_balance_service

router = APIRouter(prefix="/api/engagements/{engagement_id}/trial-balance", tags=["trial-balance"])

Reader = Annotated[
    AuthenticatedUser,
    Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER, Role.AUDITOR)),
]
Writer = Annotated[
    AuthenticatedUser, Depends(require_roles(Role.ADMIN, Role.PARTNER, Role.MANAGER))
]
Db = Annotated[AsyncSession, Depends(get_db)]


def _parse_mapping(raw: str) -> ColumnMapping:
    """The mapping arrives as a JSON form field alongside the file upload, so
    Pydantic can't validate it as a body model â€” surface its errors as 422."""
    try:
        return ColumnMapping.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Invalid column mapping",
                "errors": [error["msg"] for error in exc.errors()],
            },
        ) from exc


@router.post("/preview", response_model=TrialBalancePreview)
async def preview_file(
    engagement_id: uuid.UUID, file: UploadFile, _user: Writer, db: Db
) -> TrialBalancePreview:
    return await trial_balance_service.preview(db, engagement_id=engagement_id, file=file)


@router.post("", response_model=TrialBalanceDetail, status_code=201)
async def import_trial_balance(
    engagement_id: uuid.UUID,
    file: UploadFile,
    mapping: Annotated[str, Form()],
    user: Writer,
    db: Db,
) -> TrialBalanceDetail:
    return await trial_balance_service.import_trial_balance(
        db,
        actor=user.user_id,
        engagement_id=engagement_id,
        file=file,
        mapping=_parse_mapping(mapping),
    )


@router.get("", response_model=TrialBalanceDetail)
async def get_trial_balance(engagement_id: uuid.UUID, _user: Reader, db: Db) -> TrialBalanceDetail:
    return await trial_balance_service.get_trial_balance(db, engagement_id)


@router.get("/summary", response_model=list[FSAreaSummary])
async def get_summary(engagement_id: uuid.UUID, _user: Reader, db: Db) -> list[FSAreaSummary]:
    return await trial_balance_service.summary(db, engagement_id)


@router.patch("/fs-areas", response_model=list[TrialBalanceLineRecord])
async def update_fs_areas(
    engagement_id: uuid.UUID,
    updates: list[LineGroupingUpdate],
    user: Writer,
    db: Db,
) -> list[TrialBalanceLineRecord]:
    return await trial_balance_service.update_fs_areas(
        db, actor=user.user_id, engagement_id=engagement_id, updates=updates
    )
