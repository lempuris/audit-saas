import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.trial_balance_models import FSArea


class RiskLevel(StrEnum):
    ENTITY = "entity"
    ASSERTION = "assertion"


class RiskRating(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Assertion(StrEnum):
    EXISTENCE = "existence"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    VALUATION = "valuation"
    RIGHTS_AND_OBLIGATIONS = "rights_and_obligations"
    CUTOFF = "cutoff"
    OCCURRENCE = "occurrence"
    CLASSIFICATION = "classification"
    PRESENTATION = "presentation"


class RiskCreate(BaseModel):
    level: RiskLevel
    fs_area: FSArea | None = None
    assertions: list[Assertion] = []
    description: str = Field(min_length=1)
    inherent_rating: RiskRating
    control_rating: RiskRating
    is_significant: bool = False
    planned_response: str | None = None

    @model_validator(mode="after")
    def _assertion_level_needs_fs_area(self) -> "RiskCreate":
        if self.level == RiskLevel.ASSERTION and self.fs_area is None:
            raise ValueError("Assertion-level risks must specify an FS area")
        if self.level == RiskLevel.ENTITY and (self.fs_area or self.assertions):
            raise ValueError("Entity-level risks cannot target an FS area or assertions")
        return self


class RiskUpdate(BaseModel):
    fs_area: FSArea | None = None
    assertions: list[Assertion] | None = None
    description: str | None = Field(default=None, min_length=1)
    inherent_rating: RiskRating | None = None
    control_rating: RiskRating | None = None
    is_significant: bool | None = None
    planned_response: str | None = None


class RiskRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    level: str
    fs_area: str | None
    assertions: list[str]
    description: str
    inherent_rating: str
    control_rating: str
    combined_rating: str
    is_significant: bool
    planned_response: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
