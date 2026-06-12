import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
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


class Engagement(BaseModel):
    """One audit/review engagement for a client and fiscal year. Status
    follows the workflow enforced in engagements_service; moving to fieldwork
    requires every team member's independence confirmation."""

    __tablename__ = "engagements"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    engagement_type: Mapped[str] = mapped_column(String, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft", index=True)


class EngagementTeamMember(BaseModel):
    __tablename__ = "engagement_team_members"
    __table_args__ = (UniqueConstraint("engagement_id", "clerk_user_id"),)

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False, index=True
    )
    clerk_user_id: Mapped[str] = mapped_column(String, nullable=False)
    role_on_engagement: Mapped[str | None] = mapped_column(String, nullable=True)
    independence_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    independence_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TrialBalance(BaseModel):
    """An imported trial balance for an engagement (one per engagement —
    re-importing replaces it). Lines cascade-delete with the parent."""

    __tablename__ = "trial_balances"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), unique=True, index=True, nullable=False
    )
    source_filename: Mapped[str] = mapped_column(String, nullable=False)
    imported_by: Mapped[str] = mapped_column(String, nullable=False)  # Clerk user id


class TrialBalanceLine(BaseModel):
    """One account line. Sign convention: debit balances positive, credit
    balances negative, so a valid TB sums to zero."""

    __tablename__ = "trial_balance_lines"
    __table_args__ = (UniqueConstraint("trial_balance_id", "account_code"),)

    trial_balance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trial_balances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_code: Mapped[str] = mapped_column(String, nullable=False)
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    prior_year_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    # Financial statement area (models/trial_balance_models.FSArea); suggested
    # on import from the account name, then refined by the user.
    fs_area: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class MaterialityAssessment(BaseModel):
    """Materiality for an engagement (one per engagement). Amounts are
    computed by the service from the benchmark amount and percentages and
    stored so approved values are immutable even if the formula changes.
    Approval (Partner/Admin) locks the row until it is reopened."""

    __tablename__ = "materiality_assessments"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), unique=True, index=True, nullable=False
    )
    benchmark: Mapped[str] = mapped_column(String, nullable=False)
    benchmark_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    overall_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    overall_materiality: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    performance_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    performance_materiality: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    clearly_trivial_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    clearly_trivial_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)  # Clerk user id
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Risk(BaseModel):
    """An identified risk of material misstatement (ISA 315): entity-level or
    assertion-level (tied to an FS area and assertions). The combined rating
    is derived from inherent x control in risks_service and stored."""

    __tablename__ = "risks"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String, nullable=False)  # entity / assertion
    fs_area: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Assertion names (models/risks_models.Assertion); empty for entity-level.
    assertions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str] = mapped_column(String, nullable=False)
    inherent_rating: Mapped[str] = mapped_column(String, nullable=False)  # low/medium/high
    control_rating: Mapped[str] = mapped_column(String, nullable=False)
    combined_rating: Mapped[str] = mapped_column(String, nullable=False)
    is_significant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    planned_response: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)  # Clerk user id


class ProcedureTemplate(BaseModel):
    """Firm-wide library of ISA-referenced audit procedures per FS area,
    seeded from the built-in library and extendable by the firm. Engagement
    procedures copy a template's fields so later template edits never change
    an engagement's program."""

    __tablename__ = "procedure_templates"
    __table_args__ = (UniqueConstraint("fs_area", "title"),)

    fs_area: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    isa_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    # Assertion names addressed (models/risks_models.Assertion).
    assertions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EngagementProcedure(BaseModel):
    """A procedure on an engagement's audit program: copied from a template
    (template_id keeps provenance) or written ad hoc, then tailored, assigned
    with a due date, and tracked by status."""

    __tablename__ = "engagement_procedures"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedure_templates.id"), nullable=True
    )
    fs_area: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    isa_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    assertions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # Clerk id
    status: Mapped[str] = mapped_column(String, nullable=False, default="not_started", index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String, nullable=False)  # Clerk user id


class RiskProcedureLink(BaseModel):
    """Links a risk to a procedure that responds to it (ISA 330). Cascades
    away with either side."""

    __tablename__ = "risk_procedure_links"
    __table_args__ = (UniqueConstraint("risk_id", "procedure_id"),)

    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procedure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_procedures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


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
