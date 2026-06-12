import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from database.models import (
    Client,
    Engagement,
    EngagementProcedure,
    MaterialityAssessment,
    Risk,
    TrialBalance,
    TrialBalanceLine,
)
from database.session import get_db
from main import app
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
        "status": "planning",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_tb(engagement_id: uuid.UUID) -> TrialBalance:
    return TrialBalance(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement_id,
        source_filename="tb.csv",
        imported_by="user_test",
    )


def make_line(trial_balance_id: uuid.UUID, **overrides: Any) -> TrialBalanceLine:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "trial_balance_id": trial_balance_id,
        "account_code": "1000",
        "account_name": "Cash at bank",
        "balance": Decimal("100.00"),
        "prior_year_balance": Decimal("80.00"),
        "fs_area": "cash_and_bank",
    }
    defaults.update(overrides)
    return TrialBalanceLine(**defaults)


def make_procedure(engagement_id: uuid.UUID, **overrides: Any) -> EngagementProcedure:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "template_id": None,
        "fs_area": "revenue",
        "title": "Revenue cutoff testing",
        "description": "Test transactions either side of year end.",
        "isa_reference": "ISA 500",
        "assertions": ["cutoff"],
        "assigned_to": None,
        "status": "not_started",
        "due_date": None,
        "sort_order": 0,
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return EngagementProcedure(**defaults)


def make_risk(engagement_id: uuid.UUID, **overrides: Any) -> Risk:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "level": "assertion",
        "fs_area": "revenue",
        "assertions": ["occurrence"],
        "description": "Revenue may be overstated",
        "inherent_rating": "high",
        "control_rating": "medium",
        "combined_rating": "high",
        "is_significant": True,
        "planned_response": None,
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return Risk(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


@pytest.mark.unit
async def test_lead_schedules_require_imported_tb() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/lead-schedules", headers=bearer("auditor")
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_lead_schedule_index_totals_per_area() -> None:
    engagement = make_engagement()
    tb = make_tb(engagement.id)
    lines = [
        make_line(tb.id, account_code="1000", balance=Decimal("100.00")),
        make_line(
            tb.id,
            account_code="1010",
            balance=Decimal("50.00"),
            prior_year_balance=Decimal("70.00"),
        ),
        make_line(
            tb.id,
            account_code="4000",
            fs_area="revenue",
            balance=Decimal("-150.00"),
            prior_year_balance=Decimal("-150.00"),
        ),
        make_line(tb.id, account_code="9999", fs_area=None),
    ]
    use_db(FakeSession(rows=[engagement, tb, *lines]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/lead-schedules", headers=bearer("auditor")
        )
    assert response.status_code == 200
    body = response.json()
    # Unmapped lines are excluded; areas are sorted.
    assert [s["fs_area"] for s in body] == ["cash_and_bank", "revenue"]
    cash = body[0]
    assert cash["line_count"] == 2
    assert cash["balance"] == "150.00"
    assert cash["prior_year_balance"] == "150.00"
    assert cash["movement"] == "0.00"


@pytest.mark.unit
async def test_lead_schedule_detail_lines_sorted_with_movement() -> None:
    engagement = make_engagement()
    tb = make_tb(engagement.id)
    lines = [
        make_line(tb.id, account_code="1010", balance=Decimal("50.00"), prior_year_balance=None),
        make_line(tb.id, account_code="1000", balance=Decimal("100.00")),
    ]
    use_db(FakeSession(rows=[engagement, tb, *lines]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/lead-schedules/cash_and_bank",
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert [line["account_code"] for line in body["lines"]] == ["1000", "1010"]
    assert body["lines"][0]["movement"] == "20.00"
    assert body["lines"][1]["movement"] is None
    assert body["balance"] == "150.00"


@pytest.mark.unit
async def test_lead_schedule_unknown_area_is_404() -> None:
    engagement = make_engagement()
    tb = make_tb(engagement.id)
    use_db(FakeSession(rows=[engagement, tb, make_line(tb.id)]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/lead-schedules/inventory",
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_planning_summary_aggregates_everything() -> None:
    engagement = make_engagement()
    tb = make_tb(engagement.id)
    assessment = MaterialityAssessment(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        benchmark="revenue",
        benchmark_amount=Decimal("1000000.00"),
        overall_percentage=Decimal("1.00"),
        overall_materiality=Decimal("10000.00"),
        performance_percentage=Decimal("75.00"),
        performance_materiality=Decimal("7500.00"),
        clearly_trivial_percentage=Decimal("5.00"),
        clearly_trivial_threshold=Decimal("500.00"),
        rationale=None,
        status="approved",
        approved_by="user_partner",
        approved_at=now(),
    )
    # Two days out so the local-vs-UTC date boundary can't flip the result.
    yesterday = date.today() - timedelta(days=2)
    rows = [
        engagement,
        tb,
        make_line(tb.id),
        make_line(tb.id, account_code="9999", fs_area=None),
        assessment,
        make_risk(engagement.id),
        make_risk(
            engagement.id,
            level="entity",
            fs_area=None,
            assertions=[],
            combined_rating="medium",
            is_significant=False,
        ),
        make_procedure(engagement.id, status="completed", assigned_to="user_a"),
        make_procedure(
            engagement.id, status="in_progress", assigned_to="user_a", due_date=yesterday
        ),
        make_procedure(engagement.id),
    ]
    use_db(FakeSession(rows=rows))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/planning-summary", headers=bearer("partner")
        )
    assert response.status_code == 200
    body = response.json()
    assert body["trial_balance"] == {"imported": True, "line_count": 2, "unmapped_count": 1}
    assert body["materiality"]["status"] == "approved"
    assert body["materiality"]["overall_materiality"] == "10000.00"
    assert body["risks"]["total"] == 2
    assert body["risks"]["significant"] == 1
    assert body["risks"]["entity_level"] == 1
    assert body["risks"]["by_combined_rating"]["high"] == 1
    assert body["procedures"]["total"] == 3
    assert body["procedures"]["by_status"]["completed"] == 1
    assert body["procedures"]["overdue"] == 1
    assert body["procedures"]["unassigned"] == 1


@pytest.mark.unit
async def test_planning_summary_before_any_planning() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/planning-summary", headers=bearer("auditor")
        )
    assert response.status_code == 200
    body = response.json()
    assert body["trial_balance"]["imported"] is False
    assert body["materiality"] is None
    assert body["risks"]["total"] == 0
    assert body["procedures"]["total"] == 0


@pytest.mark.unit
async def test_my_procedures_returns_only_mine_sorted_by_due_date() -> None:
    client_row = Client(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        name="Acme Ltd",
        industry=None,
        risk_rating=None,
        contacts=[],
        archived=False,
    )
    engagement = make_engagement(client_id=client_row.id)
    soon = date.today() + timedelta(days=7)
    yesterday = date.today() - timedelta(days=2)
    mine_due = make_procedure(
        engagement.id, assigned_to="user_test", due_date=yesterday, title="Overdue one"
    )
    mine_later = make_procedure(
        engagement.id, assigned_to="user_test", due_date=soon, title="Later one"
    )
    mine_no_date = make_procedure(engagement.id, assigned_to="user_test", title="No date")
    others = make_procedure(engagement.id, assigned_to="someone_else")
    use_db(FakeSession(rows=[client_row, engagement, mine_due, mine_later, mine_no_date, others]))
    async with client() as c:
        response = await c.get("/api/my-procedures", headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert [p["title"] for p in body] == ["Overdue one", "Later one", "No date"]
    assert body[0]["overdue"] is True
    assert body[1]["overdue"] is False
    assert body[0]["client_name"] == "Acme Ltd"
    assert body[0]["engagement_id"] == str(engagement.id)


@pytest.mark.unit
async def test_my_procedures_empty() -> None:
    use_db(FakeSession(rows=[]))
    async with client() as c:
        response = await c.get("/api/my-procedures", headers=bearer("manager"))
    assert response.status_code == 200
    assert response.json() == []
