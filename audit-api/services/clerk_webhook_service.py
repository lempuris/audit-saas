"""Clerk webhook handling: Svix signature verification + user sync.

Clerk signs webhook deliveries with the Svix scheme: the signing secret is
``whsec_<base64 key>``, the signed content is ``{svix-id}.{svix-timestamp}.{body}``,
and the ``svix-signature`` header carries one or more space-separated
``v1,<base64 HMAC-SHA256>`` entries (more than one during secret rotation).
https://docs.svix.com/receiving/verifying-payloads/how-manual
"""

import base64
import hashlib
import hmac
import time

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from models.clerk_webhook_models import ClerkEvent, ClerkUserData

# Svix default tolerance: deliveries older/newer than this are replays or
# clock problems and must be rejected.
TIMESTAMP_TOLERANCE_SECONDS = 300

HANDLED_EVENTS = frozenset({"user.created", "user.updated", "user.deleted"})


class WebhookVerificationError(Exception):
    """Signature, timestamp, or header problem — the delivery is not trusted."""


def verify_webhook_signature(
    *,
    secret: str,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    body: bytes,
) -> None:
    """Raise WebhookVerificationError unless the delivery is authentic."""
    if not secret:
        # Misconfiguration, not a bad request — propagate as a 500.
        raise RuntimeError("CLERK_WEBHOOK_SECRET is not configured")
    if not (svix_id and svix_timestamp and svix_signature):
        raise WebhookVerificationError("missing svix headers")

    try:
        timestamp = int(svix_timestamp)
    except ValueError as exc:
        raise WebhookVerificationError("invalid svix-timestamp") from exc
    if abs(time.time() - timestamp) > TIMESTAMP_TOLERANCE_SECONDS:
        raise WebhookVerificationError("svix-timestamp outside tolerance")

    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed_content, hashlib.sha256).digest()).decode()

    for candidate in svix_signature.split(" "):
        version, _, signature = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(signature, expected):
            return
    raise WebhookVerificationError("no matching v1 signature")


async def apply_event(session: AsyncSession, event: ClerkEvent) -> None:
    """Sync one verified Clerk event into the users table (idempotent)."""
    if event.type not in HANDLED_EVENTS:
        return

    data = ClerkUserData.model_validate(event.data)

    if event.type == "user.deleted":
        # Keep the row so audit-trail entries can always resolve their author.
        await session.execute(
            update(User).where(User.clerk_user_id == data.id).values(is_active=False)
        )
    else:
        values = {
            "email": data.primary_email,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "role": data.role,
            "is_active": True,
        }
        statement = insert(User).values(clerk_user_id=data.id, **values)
        await session.execute(
            statement.on_conflict_do_update(index_elements=[User.clerk_user_id], set_=values)
        )
    await session.commit()
