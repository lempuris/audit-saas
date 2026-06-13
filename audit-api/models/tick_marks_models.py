import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TickMarkTargetType(StrEnum):
    TRIAL_BALANCE_LINE = "trial_balance_line"
    WORKING_PAPER = "working_paper"


class TickMarkCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=8)
    meaning: str = Field(min_length=1)
    sort_order: int = 0


class TickMarkRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    meaning: str
    sort_order: int


class SeedResult(BaseModel):
    created: int
    skipped: int


class TickMarkApplicationCreate(BaseModel):
    tick_mark_id: uuid.UUID
    target_type: TickMarkTargetType
    target_id: uuid.UUID
    note: str | None = None


class TickMarkApplicationRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    tick_mark_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    note: str | None
    applied_by: str
    created_at: datetime
    # Resolved from the tick-mark library for display.
    symbol: str = ""
    meaning: str = ""


# Common audit tick marks, seeded into the firm library (idempotent on symbol).
SEED_TICK_MARKS: list[dict] = [
    {"symbol": "✓", "meaning": "Agreed to supporting documentation", "sort_order": 10},
    {"symbol": "TB", "meaning": "Agreed to trial balance", "sort_order": 20},
    {"symbol": "PY", "meaning": "Agreed to prior-year working papers", "sort_order": 30},
    {"symbol": "F", "meaning": "Footed / recalculated total", "sort_order": 40},
    {"symbol": "CC", "meaning": "Cross-cast", "sort_order": 50},
    {"symbol": "B", "meaning": "Agreed to bank statement / confirmation", "sort_order": 60},
    {"symbol": "R", "meaning": "Recalculated", "sort_order": 70},
    {"symbol": "Cf", "meaning": "Confirmed directly with third party", "sort_order": 80},
]
