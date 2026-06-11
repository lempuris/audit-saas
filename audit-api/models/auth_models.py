from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    ADMIN = "admin"
    PARTNER = "partner"
    MANAGER = "manager"
    AUDITOR = "auditor"


class AuthenticatedUser(BaseModel):
    """Identity attached to request.state by the Clerk auth middleware."""

    user_id: str
    session_id: str | None = None
    # None when the Clerk user has no (or an unrecognised) role in its session
    # token — such users fail every require_roles() check (default deny).
    role: Role | None = None
