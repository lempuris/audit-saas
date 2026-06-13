import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.trial_balance_models import FSArea


class SampleMethod(StrEnum):
    RANDOM = "random"
    SYSTEMATIC = "systematic"
    MONETARY_UNIT = "monetary_unit"


# Poisson reliability factors at zero expected deviations, by confidence level.
RELIABILITY_FACTORS: dict[int, Decimal] = {
    80: Decimal("1.61"),
    90: Decimal("2.31"),
    95: Decimal("3.00"),
}


class SampleCreate(BaseModel):
    method: SampleMethod
    population_description: str = Field(min_length=1)
    population_value: Decimal = Field(gt=0)
    tolerable_misstatement: Decimal = Field(gt=0)
    expected_misstatement: Decimal = Field(default=Decimal(0), ge=0)
    confidence_level: int = 95
    # Item count — required to enumerate a random/systematic selection.
    population_size: int | None = Field(default=None, gt=0)
    fs_area: FSArea | None = None
    working_paper_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _validate(self) -> "SampleCreate":
        if self.confidence_level not in RELIABILITY_FACTORS:
            raise ValueError("confidence_level must be one of 80, 90, 95")
        if self.expected_misstatement >= self.tolerable_misstatement:
            raise ValueError("expected_misstatement must be below tolerable_misstatement")
        if (
            self.method in (SampleMethod.RANDOM, SampleMethod.SYSTEMATIC)
            and self.population_size is None
        ):
            raise ValueError("population_size is required for random and systematic sampling")
        return self


class SampleComputation(BaseModel):
    """Result of computing a sample without storing it."""

    method: str
    sample_size: int
    reliability_factor: Decimal
    selection_basis: dict[str, Any]


class SampleRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    working_paper_id: uuid.UUID | None
    fs_area: str | None
    population_description: str
    method: str
    population_size: int | None
    population_value: Decimal
    tolerable_misstatement: Decimal
    expected_misstatement: Decimal
    confidence_level: int
    reliability_factor: Decimal
    sample_size: int
    selection_basis: dict[str, Any]
    created_by: str
    created_at: datetime
