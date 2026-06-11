import io
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from openpyxl import Workbook

from database.models import Engagement, TrialBalance, TrialBalanceLine
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client

BALANCED_CSV = (
    "code,name,balance,prior\n"
    '1000,Cash at bank,"1,000.00",800.00\n'
    "1100,Trade receivables,500.00,600.00\n"
    ",TOTAL,0.00,\n"
    "3000,Share capital,(1500.00),(1400.00)\n"
)
BALANCE_MAPPING = json.dumps(
    {
        "account_code": "code",
        "account_name": "name",
        "balance": "balance",
        "prior_year_balance": "prior",
    }
)


def now() -> datetime:
    return datetime.now(UTC)


def make_engagement(**overrides: Any) -> Engagement:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "client_id": uuid.uuid4(),
        "engagement_type": "audit",
        "fiscal_year": 2026,
        "status": "planning",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_trial_balance(engagement_id: uuid.UUID, **overrides: Any) -> TrialBalance:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "source_filename": "tb.csv",
        "imported_by": "user_test",
    }
    defaults.update(overrides)
    return TrialBalance(**defaults)


def make_line(trial_balance_id: uuid.UUID, **overrides: Any) -> TrialBalanceLine:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "trial_balance_id": trial_balance_id,
        "account_code": "1000",
        "account_name": "Cash at bank",
        "balance": Decimal("100.00"),
        "prior_year_balance": None,
        "fs_area": "cash_and_bank",
    }
    defaults.update(overrides)
    return TrialBalanceLine(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def csv_upload(content: str, filename: str = "tb.csv") -> dict[str, Any]:
    return {"file": (filename, content.encode(), "text/csv")}


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/trial-balance{suffix}"


@pytest.mark.unit
async def test_auditor_cannot_import() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": BALANCE_MAPPING},
            headers=bearer("auditor"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_preview_returns_columns_and_rows() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            files=csv_upload(BALANCED_CSV),
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["code", "name", "balance", "prior"]
    assert body["total_rows"] == 4
    assert body["rows"][0] == {
        "code": "1000",
        "name": "Cash at bank",
        "balance": "1,000.00",
        "prior": "800.00",
    }


@pytest.mark.unit
async def test_import_csv_creates_lines_with_suggested_areas() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": BALANCE_MAPPING},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["source_filename"] == "tb.csv"
    # The TOTAL row has no account code, so it is skipped.
    by_code = {line["account_code"]: line for line in body["lines"]}
    assert sorted(by_code) == ["1000", "1100", "3000"]
    assert by_code["1000"]["balance"] == "1000.00"
    assert by_code["1000"]["fs_area"] == "cash_and_bank"
    assert by_code["1100"]["fs_area"] == "trade_receivables"
    assert by_code["3000"]["balance"] == "-1500.00"
    assert by_code["3000"]["prior_year_balance"] == "-1400.00"
    assert by_code["3000"]["fs_area"] == "equity"
    audit = next(o for o in session.added if type(o).__name__ == "AuditTrailEntry")
    assert audit.entity_type == "trial_balance"
    assert audit.action == "create"
    assert session.committed


@pytest.mark.unit
async def test_unbalanced_tb_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    unbalanced = "code,name,balance\n1000,Cash,100.00\n3000,Capital,-50.00\n"
    mapping = json.dumps({"account_code": "code", "account_name": "name", "balance": "balance"})
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(unbalanced),
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
    assert "does not balance" in response.json()["detail"]["errors"][0]


@pytest.mark.unit
async def test_debit_credit_mapping() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    content = (
        "Acct,Description,Debit,Credit\n1000,Cash at bank,250.00,\n4000,Sales revenue,,250.00\n"
    )
    mapping = json.dumps(
        {
            "account_code": "Acct",
            "account_name": "Description",
            "debit": "Debit",
            "credit": "Credit",
        }
    )
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(content),
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    by_code = {line["account_code"]: line for line in response.json()["lines"]}
    assert by_code["1000"]["balance"] == "250.00"
    assert by_code["4000"]["balance"] == "-250.00"
    assert by_code["4000"]["fs_area"] == "revenue"


@pytest.mark.unit
async def test_mapping_without_amount_columns_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    mapping = json.dumps({"account_code": "code", "account_name": "name"})
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Invalid column mapping"


@pytest.mark.unit
async def test_mapped_column_missing_from_file_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    mapping = json.dumps({"account_code": "code", "account_name": "name", "balance": "amount"})
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
    assert "'amount' not found" in response.json()["detail"]["errors"][0]


@pytest.mark.unit
async def test_duplicate_account_codes_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    content = "code,name,balance\n1000,Cash,100.00\n1000,Cash again,-100.00\n"
    mapping = json.dumps({"account_code": "code", "account_name": "name", "balance": "balance"})
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(content),
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
    assert "duplicate account code '1000'" in response.json()["detail"]["errors"][0]


@pytest.mark.unit
async def test_unsupported_file_type_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload("not a tb", filename="tb.pdf"),
            data={"mapping": BALANCE_MAPPING},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]["errors"][0]


@pytest.mark.unit
async def test_import_blocked_on_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": BALANCE_MAPPING},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_reimport_replaces_existing_trial_balance() -> None:
    engagement = make_engagement()
    existing = make_trial_balance(engagement.id, source_filename="old.csv")
    session = FakeSession(rows=[engagement, existing])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files=csv_upload(BALANCED_CSV),
            data={"mapping": BALANCE_MAPPING},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    assert existing in session.deleted
    deletions = [
        o for o in session.added if type(o).__name__ == "AuditTrailEntry" and o.action == "delete"
    ]
    assert len(deletions) == 1
    assert deletions[0].before["source_filename"] == "old.csv"


@pytest.mark.unit
async def test_import_xlsx() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["code", "name", "balance"])
    sheet.append(["1000", "Cash at bank", 750])
    sheet.append(["3000", "Share capital", -750])
    buffer = io.BytesIO()
    workbook.save(buffer)
    mapping = json.dumps({"account_code": "code", "account_name": "name", "balance": "balance"})
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            files={
                "file": (
                    "tb.xlsx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"mapping": mapping},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    by_code = {line["account_code"]: line for line in response.json()["lines"]}
    assert by_code["1000"]["balance"] == "750.00"
    assert by_code["1000"]["fs_area"] == "cash_and_bank"


@pytest.mark.unit
async def test_get_without_import_returns_404() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 404


@pytest.mark.unit
async def test_get_returns_lines() -> None:
    engagement = make_engagement()
    trial_balance = make_trial_balance(engagement.id)
    line = make_line(trial_balance.id)
    use_db(FakeSession(rows=[engagement, trial_balance, line]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert body["source_filename"] == "tb.csv"
    assert len(body["lines"]) == 1
    assert body["lines"][0]["account_code"] == "1000"


@pytest.mark.unit
async def test_summary_groups_by_area_with_movement() -> None:
    engagement = make_engagement()
    trial_balance = make_trial_balance(engagement.id)
    rows = [
        engagement,
        trial_balance,
        make_line(
            trial_balance.id,
            account_code="1000",
            balance=Decimal("600.00"),
            prior_year_balance=Decimal("400.00"),
            fs_area="cash_and_bank",
        ),
        make_line(
            trial_balance.id,
            account_code="1010",
            account_name="Petty cash",
            balance=Decimal("100.00"),
            prior_year_balance=Decimal("150.00"),
            fs_area="cash_and_bank",
        ),
        make_line(
            trial_balance.id,
            account_code="9999",
            account_name="Suspense",
            balance=Decimal("-700.00"),
            prior_year_balance=None,
            fs_area=None,
        ),
    ]
    use_db(FakeSession(rows=rows))
    async with client() as c:
        response = await c.get(url(engagement.id, "/summary"), headers=bearer("auditor"))
    assert response.status_code == 200
    by_area = {item["fs_area"]: item for item in response.json()}
    cash = by_area["cash_and_bank"]
    assert cash["line_count"] == 2
    assert cash["balance"] == "700.00"
    assert cash["prior_year_balance"] == "550.00"
    assert cash["movement"] == "150.00"
    unmapped = by_area[None]
    assert unmapped["prior_year_balance"] is None
    assert unmapped["movement"] is None


@pytest.mark.unit
async def test_update_fs_areas() -> None:
    engagement = make_engagement()
    trial_balance = make_trial_balance(engagement.id)
    line = make_line(trial_balance.id, fs_area=None, account_name="Suspense")
    session = FakeSession(rows=[engagement, trial_balance, line])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, "/fs-areas"),
            json=[{"line_id": str(line.id), "fs_area": "other_assets"}],
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    assert line.fs_area == "other_assets"
    audit = next(o for o in session.added if type(o).__name__ == "AuditTrailEntry")
    assert audit.action == "update"
    assert audit.after == {"fs_areas": {str(line.id): "other_assets"}}
    assert session.committed


@pytest.mark.unit
async def test_update_fs_areas_unknown_line_404() -> None:
    engagement = make_engagement()
    trial_balance = make_trial_balance(engagement.id)
    use_db(FakeSession(rows=[engagement, trial_balance]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, "/fs-areas"),
            json=[{"line_id": str(uuid.uuid4()), "fs_area": "equity"}],
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_invalid_fs_area_rejected() -> None:
    engagement = make_engagement()
    trial_balance = make_trial_balance(engagement.id)
    line = make_line(trial_balance.id)
    use_db(FakeSession(rows=[engagement, trial_balance, line]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, "/fs-areas"),
            json=[{"line_id": str(line.id), "fs_area": "not_an_area"}],
            headers=bearer("manager"),
        )
    assert response.status_code == 422
