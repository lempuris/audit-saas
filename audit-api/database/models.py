import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    """Abstract base: UUID PK + created_at/updated_at on every table."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(BaseModel):
    """Local mirror of a Clerk user, kept in sync by the Clerk webhook.

    Rows are never deleted: user.deleted flips is_active so audit-trail rows
    can always resolve their author.
    """

    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Raw role string from Clerk public_metadata; not an enum column so a
    # role added in Clerk before a deploy doesn't break the sync.
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Client(BaseModel):
    """An audit client of the firm. Never hard-deleted — DELETE archives, so
    engagement history stays intact."""

    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_rating: Mapped[str | None] = mapped_column(String, nullable=True)  # low/medium/high
    # [{"name": ..., "email": ..., "phone": ..., "position": ...}]
    contacts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AuditTrailEntry(BaseModel):
    """Immutable record of a write or login. The application only ever
    inserts; there are no update/delete paths."""

    __tablename__ = "audit_trail"

    actor_clerk_user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # create/update/delete/login
    entity_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
