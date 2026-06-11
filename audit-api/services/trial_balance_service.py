"""Trial balance import: parse XLSX/CSV, validate against a user-supplied
column mapping, suggest a financial-statement area per line, and serve
per-area totals with prior-year comparison.

Sign convention throughout: debit balances positive, credit balances
negative â€” a valid TB therefore sums to zero (enforced on import). Rows with
an empty account-code cell are skipped (subtotal/total rows). Re-importing
replaces the engagement's existing TB, including manual area groupings.
"""

import csv
import io
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, UploadFile, status
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Engagement, TrialBalance, TrialBalanceLine
from models.engagements_models import EngagementStatus
from models.trial_balance_models import (
    ColumnMapping,
    FSArea,
    FSAreaSummary,
    LineGroupingUpdate,
    TrialBalanceDetail,
    TrialBalanceLineRecord,
    TrialBalancePreview,
)
from services import audit_trail_service

ENTITY_TYPE = "trial_balance"
PREVIEW_ROWS = 10
TWO_DP = Decimal("0.01")

# First match (case-insensitive substring of the account name) wins, so more
# specific phrases must precede the generic words they contain
# ("cost of sales" before "sales", "interest income" before "interest").
_FS_AREA_KEYWORDS: list[tuple[str, FSArea]] = [
    ("cost of sales", FSArea.COST_OF_SALES),
    ("cost of goods", FSArea.COST_OF_SALES),
    ("interest income", FSArea.OTHER_INCOME),
    ("interest receivable", FSArea.OTHER_ASSETS),
    ("share capital", FSArea.EQUITY),
    ("retained earning", FSArea.EQUITY),
    ("revaluation", FSArea.EQUITY),
    ("reserve", FSArea.EQUITY),
    ("dividend", FSArea.EQUITY),
    ("goodwill", FSArea.INTANGIBLE_ASSETS),
    ("intangible", FSArea.INTANGIBLE_ASSETS),
    ("software", FSArea.INTANGIBLE_ASSETS),
    ("investment", FSArea.INVESTMENTS),
    ("property", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("plant", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("equipment", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("machinery", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("vehicle", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("land", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("building", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("depreciation", FSArea.PROPERTY_PLANT_EQUIPMENT),
    ("amortisation", FSArea.INTANGIBLE_ASSETS),
    ("inventory", FSArea.INVENTORY),
    ("stock", FSArea.INVENTORY),
    ("receivable", FSArea.TRADE_RECEIVABLES),
    ("debtor", FSArea.TRADE_RECEIVABLES),
    ("prepay", FSArea.OTHER_ASSETS),
    ("prepaid", FSArea.OTHER_ASSETS),
    ("deposit", FSArea.OTHER_ASSETS),
    ("cash", FSArea.CASH_AND_BANK),
    ("bank", FSArea.CASH_AND_BANK),
    ("petty", FSArea.CASH_AND_BANK),
    ("overdraft", FSArea.BORROWINGS),
    ("loan", FSArea.BORROWINGS),
    ("borrowing", FSArea.BORROWINGS),
    ("lease liab", FSArea.BORROWINGS),
    ("payable", FSArea.TRADE_PAYABLES),
    ("creditor", FSArea.TRADE_PAYABLES),
    ("accrual", FSArea.OTHER_LIABILITIES),
    ("accrued", FSArea.OTHER_LIABILITIES),
    ("deferred income", FSArea.OTHER_LIABILITIES),
    ("provision", FSArea.PROVISIONS),
    ("vat", FSArea.OTHER_LIABILITIES),
    ("paye", FSArea.OTHER_LIABILITIES),
    ("tax", FSArea.TAX),
    ("revenue", FSArea.REVENUE),
    ("sales", FSArea.REVENUE),
    ("turnover", FSArea.REVENUE),
    ("fees earned", FSArea.REVENUE),
    ("purchases", FSArea.COST_OF_SALES),
    ("interest", FSArea.FINANCE_COSTS),
    ("finance cost", FSArea.FINANCE_COSTS),
    ("salar", FSArea.OPERATING_EXPENSES),
    ("wage", FSArea.OPERATING_EXPENSES),
    ("rent", FSArea.OPERATING_EXPENSES),
    ("utilit", FSArea.OPERATING_EXPENSES),
    ("insurance", FSArea.OPERATING_EXPENSES),
    ("repair", FSArea.OPERATING_EXPENSES),
    ("travel", FSArea.OPERATING_EXPENSES),
    ("expense", FSArea.OPERATING_EXPENSES),
]


def suggest_fs_area(account_name: str) -> str | None:
    name = account_name.lower()
    for keyword, area in _FS_AREA_KEYWORDS:
        if keyword in name:
            return area
    return None


def _validation_error(errors: list[str]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"message": "Trial balance validation failed", "errors": errors},
    )


def _cell_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_amount(value: object) -> Decimal:
    """Parse a spreadsheet amount cell. Empty cells are zero; parentheses
    and a trailing minus both mean negative; thousands separators ignored.
    Raises ValueError on anything else non-numeric."""
    if value is None:
        return Decimal("0")
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value)).quantize(TWO_DP)
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text:
        return Decimal("0")
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    elif text.endswith("-"):
        negative = True
        text = text[:-1]
    try:
        amount = Decimal(text).quantize(TWO_DP)
    except InvalidOperation as exc:
        raise ValueError(f"'{value}' is not a number") from exc
    return -amount if negative else amount


async def _read_rows(file: UploadFile) -> tuple[list[str], list[dict[str, object]]]:
    """Parse an uploaded CSV/XLSX into (headers, rows-as-dicts). The first
    non-empty row is the header; duplicate headers are rejected because they
    make the column mapping ambiguous."""
    filename = file.filename or ""
    content = await file.read()
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if suffix == "csv":
        try:
            raw_rows: list[list[object]] = list(
                csv.reader(io.StringIO(content.decode("utf-8-sig")))
            )
        except UnicodeDecodeError:
            raise _validation_error(["File is not valid UTF-8 text"]) from None
    elif suffix == "xlsx":
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception:
            raise _validation_error(["File is not a valid .xlsx workbook"]) from None
        raw_rows = [list(row) for row in workbook.worksheets[0].iter_rows(values_only=True)]
        workbook.close()
    else:
        raise _validation_error(
            [f"Unsupported file type '{filename}': upload a .xlsx or .csv file"]
        )

    raw_rows = [row for row in raw_rows if any(_cell_text(cell) for cell in row)]
    if not raw_rows:
        raise _validation_error(["File contains no data"])

    headers = [_cell_text(cell) or f"column_{i + 1}" for i, cell in enumerate(raw_rows[0])]
    duplicates = sorted({h for h in headers if headers.count(h) > 1})
    if duplicates:
        raise _validation_error([f"Duplicate column headers: {', '.join(duplicates)}"])

    rows = [
        {header: (row[i] if i < len(row) else None) for i, header in enumerate(headers)}
        for row in raw_rows[1:]
    ]
    return headers, rows


async def _get_engagement(session: AsyncSession, engagement_id: uuid.UUID) -> Engagement:
    engagement = (
        await session.scalars(select(Engagement).where(Engagement.id == engagement_id))
    ).first()
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return engagement


async def _get_trial_balance(
    session: AsyncSession, engagement_id: uuid.UUID
) -> TrialBalance | None:
    return (
        await session.scalars(
            select(TrialBalance).where(TrialBalance.engagement_id == engagement_id)
        )
    ).first()


async def _lines(session: AsyncSession, trial_balance_id: uuid.UUID) -> list[TrialBalanceLine]:
    rows = await session.scalars(
        select(TrialBalanceLine)
        .where(TrialBalanceLine.trial_balance_id == trial_balance_id)
        .order_by(TrialBalanceLine.account_code)
    )
    return list(rows)


def _detail(trial_balance: TrialBalance, lines: list[TrialBalanceLine]) -> TrialBalanceDetail:
    detail = TrialBalanceDetail.model_validate(trial_balance)
    detail.lines = [TrialBalanceLineRecord.model_validate(line) for line in lines]
    return detail


async def preview(
    session: AsyncSession, *, engagement_id: uuid.UUID, file: UploadFile
) -> TrialBalancePreview:
    await _get_engagement(session, engagement_id)
    headers, rows = await _read_rows(file)
    return TrialBalancePreview(
        columns=headers,
        rows=[
            {header: _cell_text(row[header]) for header in headers} for row in rows[:PREVIEW_ROWS]
        ],
        total_rows=len(rows),
    )


def _build_lines(
    headers: list[str], rows: list[dict[str, object]], mapping: ColumnMapping
) -> list[TrialBalanceLine]:
    mapped_columns = [
        column
        for column in (
            mapping.account_code,
            mapping.account_name,
            mapping.balance,
            mapping.debit,
            mapping.credit,
            mapping.prior_year_balance,
        )
        if column is not None
    ]
    missing = [column for column in mapped_columns if column not in headers]
    if missing:
        raise _validation_error(
            [f"Mapped column '{column}' not found in the file" for column in missing]
        )

    errors: list[str] = []
    lines: list[TrialBalanceLine] = []
    seen_codes: dict[str, int] = {}

    for index, row in enumerate(rows):
        row_number = index + 2  # 1-based, after the header row
        code = _cell_text(row[mapping.account_code])
        if code is None:
            continue  # subtotal/total/blank rows carry no account code

        if code in seen_codes:
            errors.append(
                f"Row {row_number}: duplicate account code '{code}' (first seen on row "
                f"{seen_codes[code]})"
            )
            continue
        seen_codes[code] = row_number

        name = _cell_text(row[mapping.account_name]) or code
        try:
            if mapping.balance is not None:
                balance = _parse_amount(row[mapping.balance])
            else:
                # ColumnMapping guarantees debit and credit are both set here.
                balance = _parse_amount(row[mapping.debit]) - _parse_amount(row[mapping.credit])
            prior = (
                _parse_amount(row[mapping.prior_year_balance])
                if mapping.prior_year_balance is not None
                else None
            )
        except ValueError as exc:
            errors.append(f"Row {row_number}: {exc}")
            continue

        lines.append(
            TrialBalanceLine(
                id=uuid.uuid4(),
                account_code=code,
                account_name=name,
                balance=balance,
                prior_year_balance=prior,
                fs_area=suggest_fs_area(name),
            )
        )

    if errors:
        raise _validation_error(errors)
    if not lines:
        raise _validation_error(["No account lines found (every row has an empty account code)"])

    total = sum((line.balance for line in lines), Decimal("0"))
    if total != 0:
        raise _validation_error(
            [f"Trial balance does not balance: debits and credits differ by {total}"]
        )
    return lines


async def import_trial_balance(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    file: UploadFile,
    mapping: ColumnMapping,
) -> TrialBalanceDetail:
    engagement = await _get_engagement(session, engagement_id)
    if engagement.status == EngagementStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot import a trial balance into a completed engagement",
        )

    headers, rows = await _read_rows(file)
    lines = _build_lines(headers, rows, mapping)

    existing = await _get_trial_balance(session, engagement_id)
    if existing is not None:
        audit_trail_service.record(
            session,
            actor=actor,
            action="delete",
            entity_type=ENTITY_TYPE,
            entity_id=str(existing.id),
            before={
                "engagement_id": str(engagement_id),
                "source_filename": existing.source_filename,
            },
        )
        # Lines go with it via ON DELETE CASCADE.
        await session.delete(existing)

    trial_balance = TrialBalance(
        id=uuid.uuid4(),
        engagement_id=engagement_id,
        source_filename=file.filename or "upload",
        imported_by=actor,
    )
    for line in lines:
        line.trial_balance_id = trial_balance.id
    session.add(trial_balance)
    for line in lines:
        session.add(line)

    audit_trail_service.record(
        session,
        actor=actor,
        action="create",
        entity_type=ENTITY_TYPE,
        entity_id=str(trial_balance.id),
        after={
            "engagement_id": str(engagement_id),
            "source_filename": trial_balance.source_filename,
            "line_count": len(lines),
        },
    )
    await session.commit()
    await session.refresh(trial_balance)
    return _detail(trial_balance, lines)


async def get_trial_balance(session: AsyncSession, engagement_id: uuid.UUID) -> TrialBalanceDetail:
    await _get_engagement(session, engagement_id)
    trial_balance = await _get_trial_balance(session, engagement_id)
    if trial_balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trial balance imported for this engagement",
        )
    return _detail(trial_balance, await _lines(session, trial_balance.id))


async def summary(session: AsyncSession, engagement_id: uuid.UUID) -> list[FSAreaSummary]:
    """Totals per FS area with prior-year movement. TBs are small (hundreds
    of lines), so aggregation in Python is fine."""
    detail = await get_trial_balance(session, engagement_id)
    groups: dict[str | None, list[TrialBalanceLineRecord]] = {}
    for line in detail.lines:
        groups.setdefault(line.fs_area, []).append(line)

    summaries = []
    for area, lines in sorted(groups.items(), key=lambda item: item[0] or "~unmapped"):
        priors = [line.prior_year_balance for line in lines if line.prior_year_balance is not None]
        balance = sum((line.balance for line in lines), Decimal("0"))
        prior_total = sum(priors, Decimal("0")) if priors else None
        summaries.append(
            FSAreaSummary(
                fs_area=area,
                line_count=len(lines),
                balance=balance,
                prior_year_balance=prior_total,
                movement=(balance - prior_total) if prior_total is not None else None,
            )
        )
    return summaries


async def update_fs_areas(
    session: AsyncSession,
    *,
    actor: str,
    engagement_id: uuid.UUID,
    updates: list[LineGroupingUpdate],
) -> list[TrialBalanceLineRecord]:
    await _get_engagement(session, engagement_id)
    trial_balance = await _get_trial_balance(session, engagement_id)
    if trial_balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trial balance imported for this engagement",
        )

    lines = await _lines(session, trial_balance.id)
    by_id = {line.id: line for line in lines}
    unknown = [str(update.line_id) for update in updates if update.line_id not in by_id]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trial balance lines not found: {', '.join(unknown)}",
        )

    before: dict[str, str | None] = {}
    after: dict[str, str | None] = {}
    for update in updates:
        line = by_id[update.line_id]
        new_area = update.fs_area.value if update.fs_area is not None else None
        if line.fs_area == new_area:
            continue
        before[str(line.id)] = line.fs_area
        after[str(line.id)] = new_area
        line.fs_area = new_area

    if after:
        audit_trail_service.record(
            session,
            actor=actor,
            action="update",
            entity_type=ENTITY_TYPE,
            entity_id=str(trial_balance.id),
            before={"fs_areas": before},
            after={"fs_areas": after},
        )
        await session.commit()
    return [TrialBalanceLineRecord.model_validate(line) for line in lines]
