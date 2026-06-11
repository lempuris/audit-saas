import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class FSArea(StrEnum):
    """Financial statement areas used to group TB lines (and, in Phase 3,
    to index lead schedules and working papers)."""

    PROPERTY_PLANT_EQUIPMENT = "property_plant_equipment"
    INTANGIBLE_ASSETS = "intangible_assets"
    INVESTMENTS = "investments"
    INVENTORY = "inventory"
    TRADE_RECEIVABLES = "trade_receivables"
    CASH_AND_BANK = "cash_and_bank"
    OTHER_ASSETS = "other_assets"
    TRADE_PAYABLES = "trade_payables"
    BORROWINGS = "borrowings"
    PROVISIONS = "provisions"
    OTHER_LIABILITIES = "other_liabilities"
    EQUITY = "equity"
    REVENUE = "revenue"
    COST_OF_SALES = "cost_of_sales"
    OPERATING_EXPENSES = "operating_expenses"
    OTHER_INCOME = "other_income"
    FINANCE_COSTS = "finance_costs"
    TAX = "tax"


class ColumnMapping(BaseModel):
    """Maps spreadsheet header names to TB fields. Amounts come either from a
    single signed `balance` column or from separate `debit`/`credit` columns."""

    account_code: str
    account_name: str
    balance: str | None = None
    debit: str | None = None
    credit: str | None = None
    prior_year_balance: str | None = None

    @model_validator(mode="after")
    def _require_amount_columns(self) -> "ColumnMapping":
        if self.balance is None and not (self.debit and self.credit):
            raise ValueError("Map either a balance column or both debit and credit columns")
        return self


class TrialBalancePreview(BaseModel):
    """Detected columns plus the first rows, for the column-mapping UI."""

    columns: list[str]
    rows: list[dict[str, str | None]]
    total_rows: int


class TrialBalanceLineRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_code: str
    account_name: str
    balance: Decimal
    prior_year_balance: Decimal | None
    fs_area: str | None


class TrialBalanceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    source_filename: str
    imported_by: str
    created_at: datetime
    updated_at: datetime


class TrialBalanceDetail(TrialBalanceRecord):
    lines: list[TrialBalanceLineRecord] = []


class FSAreaSummary(BaseModel):
    """Per-area totals with prior-year comparison. `fs_area` None groups the
    not-yet-mapped lines; prior fields are None when no prior-year column
    was imported."""

    fs_area: str | None
    line_count: int
    balance: Decimal
    prior_year_balance: Decimal | None
    movement: Decimal | None


class LineGroupingUpdate(BaseModel):
    line_id: uuid.UUID
    fs_area: FSArea | None  # None ungroups the line
