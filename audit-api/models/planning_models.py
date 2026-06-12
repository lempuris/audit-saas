import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class LeadScheduleLine(BaseModel):
    """One TB account on a lead schedule, with prior-year movement."""

    line_id: uuid.UUID
    account_code: str
    account_name: str
    balance: Decimal
    prior_year_balance: Decimal | None
    movement: Decimal | None


class LeadScheduleSummary(BaseModel):
    fs_area: str
    line_count: int
    balance: Decimal
    prior_year_balance: Decimal | None
    movement: Decimal | None


class LeadSchedule(LeadScheduleSummary):
    lines: list[LeadScheduleLine]


class TrialBalanceProgress(BaseModel):
    imported: bool
    line_count: int
    unmapped_count: int


class MaterialityProgress(BaseModel):
    status: str
    overall_materiality: Decimal
    performance_materiality: Decimal
    clearly_trivial_threshold: Decimal


class RiskProgress(BaseModel):
    total: int
    significant: int
    entity_level: int
    assertion_level: int
    by_combined_rating: dict[str, int]


class ProcedureProgress(BaseModel):
    total: int
    by_status: dict[str, int]
    overdue: int
    unassigned: int


class PlanningSummary(BaseModel):
    """Planning dashboard for one engagement: where each Phase 2 deliverable
    stands. materiality is None until an assessment exists."""

    engagement_id: uuid.UUID
    engagement_status: str
    trial_balance: TrialBalanceProgress
    materiality: MaterialityProgress | None
    risks: RiskProgress
    procedures: ProcedureProgress


class MyProcedure(BaseModel):
    """A procedure assigned to the caller, across engagements."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    engagement_status: str
    fiscal_year: int
    client_name: str | None
    fs_area: str
    title: str
    isa_reference: str | None
    status: str
    due_date: date | None
    overdue: bool
