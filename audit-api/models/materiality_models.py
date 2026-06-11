import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MaterialityBenchmark(StrEnum):
    REVENUE = "revenue"
    TOTAL_ASSETS = "total_assets"
    PROFIT_BEFORE_TAX = "profit_before_tax"
    EQUITY = "equity"
    TOTAL_EXPENSES = "total_expenses"
    CUSTOM = "custom"


class MaterialityStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class MaterialityInput(BaseModel):
    """Inputs for the materiality calculation. The service derives the amounts
    (overall, performance, clearly-trivial) — clients never send them."""

    benchmark: MaterialityBenchmark
    benchmark_amount: Decimal = Field(gt=0)
    overall_percentage: Decimal = Field(gt=0, le=100)
    # Percentage of overall materiality, per common practice 50–75%.
    performance_percentage: Decimal = Field(gt=0, le=100)
    # Percentage of overall materiality, typically around 5%.
    clearly_trivial_percentage: Decimal = Field(gt=0, le=100)
    rationale: str | None = None


class MaterialityRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    benchmark: str
    benchmark_amount: Decimal
    overall_percentage: Decimal
    overall_materiality: Decimal
    performance_percentage: Decimal
    performance_materiality: Decimal
    clearly_trivial_percentage: Decimal
    clearly_trivial_threshold: Decimal
    rationale: str | None
    status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
