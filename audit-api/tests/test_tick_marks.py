import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from database.models import (
    AuditTrailEntry,
    Engagement,
    TickMark,
    TickMarkApplication,
    TrialBalance,
    TrialBalanceLine,
)
from database.session import get_db
from main import app
from models.tick_marks_models import SEED_TICK_MARKS
from tests.conftest import FakeSession, bearer, client


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
        "status": "fieldwork",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_mark(**overrides: Any) -> TickMark:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "symbol": "✓",
        "meaning": "Agreed to supporting documentation",
        "sort_order": 10,
    }
    defaults.update(overrides)
    return TickMark(**defaults)


def make_tb(engagement_id: uuid.UUID, **overrides: Any) -> TrialBalance:
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


def app_url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/tick-mark-applications{suffix}"


@pytest.mark.unit
async def test_seed_creates_library_once() -> None:
    session = FakeSession(rows=[])
    use_db(session)
    async with client() as c:
        response = await c.post("/api/tick-marks/seed", headers=bearer("manager"))
    assert response.status_code == 200
    assert response.json()["created"] == len(SEED_TICK_MARKS)


@pytest.mark.unit
async def test_auditor_cannot_curate_library() -> None:
    use_db(FakeSession(rows=[]))
    async with client() as c:
        response = await c.post("/api/tick-marks/seed", headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_apply_to_tb_line_resolves_symbol() -> None:
    engagement = make_engagement()
    mark = make_mark()
    tb = make_tb(engagement.id)
    line = make_line(tb.id)
    session = FakeSession(rows=[engagement, mark, tb, line])
    use_db(session)
    async with client() as c:
        response = await c.post(
            app_url(engagement.id),
            json={
                "tick_mark_id": str(mark.id),
                "target_type": "trial_balance_line",
                "target_id": str(line.id),
                "note": "Vouched to invoice",
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["symbol"] == "✓"
    assert body["meaning"] == "Agreed to supporting documentation"
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_apply_to_foreign_line_is_404() -> None:
    engagement = make_engagement()
    mark = make_mark()
    other_tb = make_tb(uuid.uuid4())
    line = make_line(other_tb.id)
    # No trial balance for this engagement.
    use_db(FakeSession(rows=[engagement, mark, line]))
    async with client() as c:
        response = await c.post(
            app_url(engagement.id),
            json={
                "tick_mark_id": str(mark.id),
                "target_type": "trial_balance_line",
                "target_id": str(line.id),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_duplicate_application_is_409() -> None:
    engagement = make_engagement()
    mark = make_mark()
    tb = make_tb(engagement.id)
    line = make_line(tb.id)
    existing = TickMarkApplication(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        tick_mark_id=mark.id,
        target_type="trial_balance_line",
        target_id=line.id,
        note=None,
        applied_by="user_test",
    )
    use_db(FakeSession(rows=[engagement, mark, tb, line, existing]))
    async with client() as c:
        response = await c.post(
            app_url(engagement.id),
            json={
                "tick_mark_id": str(mark.id),
                "target_type": "trial_balance_line",
                "target_id": str(line.id),
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_remove_application_writes_audit_row() -> None:
    engagement = make_engagement()
    application = TickMarkApplication(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        tick_mark_id=uuid.uuid4(),
        target_type="trial_balance_line",
        target_id=uuid.uuid4(),
        note=None,
        applied_by="user_test",
    )
    session = FakeSession(rows=[engagement, application])
    use_db(session)
    async with client() as c:
        response = await c.delete(
            app_url(engagement.id, f"/{application.id}"), headers=bearer("auditor")
        )
    assert response.status_code == 204
    assert application in session.deleted
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "delete"
