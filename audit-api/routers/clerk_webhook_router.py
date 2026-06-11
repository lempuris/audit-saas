from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.session import get_db
from models.clerk_webhook_models import ClerkEvent
from services.clerk_webhook_service import (
    WebhookVerificationError,
    apply_event,
    verify_webhook_signature,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/clerk", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    body = await request.body()
    try:
        verify_webhook_signature(
            secret=get_settings().clerk_webhook_secret,
            svix_id=request.headers.get("svix-id", ""),
            svix_timestamp=request.headers.get("svix-timestamp", ""),
            svix_signature=request.headers.get("svix-signature", ""),
            body=body,
        )
    except WebhookVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        ) from exc

    await apply_event(db, ClerkEvent.model_validate_json(body))
