import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from database.models import (
    Client,
    Engagement,
    EngagementProcedure,
    ReviewNote,
    User,
    WorkingPaper,
)
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client


def now() -> datetime:
    return datetime.now(UTC)


def make_client(**overrides: Any) -> Client:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "name": "Acme Ltd",
        "industry": "manufacturing",
        "risk_rating": "medium",
        "contacts": [],
        "archived": False,
    }
    defaults.update(overrides)
    return Client(**defaults)


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


def make_paper(engagement_id: uuid.UUID, **overrides: Any) -> WorkingPaper:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "fs_area": "cash_and_bank",
        "index_ref": "A-1",
        "title": "Bank reconciliation",
        "objective": "Verify cash",
        "result": "Reconciled",
        "conclusion": "No exceptions",
        "status": "prepared",
        "prepared_by": "user_aud",
        "prepared_at": now(),
        "created_by": "user_aud",
    }
    defaults.update(overrides)
    return WorkingPaper(**defaults)


def make_procedure(engagement_id: uuid.UUID, **overrides: Any) -> EngagementProcedure:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "fs_area": "cash_and_bank",
        "title": "Confirm bank balances",
        "description": "Send confirmations",
        "isa_reference": "ISA 505",
        "assertions": [],
        "assigned_to": "user_aud",
        "status": "in_progress",
        "due_date": date.today() - timedelta(days=5),
        "sort_order": 0,
        "created_by": "user_mgr",
    }
    defaults.update(overrides)
    return EngagementProcedure(**defaults)


def make_note(engagement_id: uuid.UUID, **overrides: Any) -> ReviewNote:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "working_paper_id": None,
        "text": "Explain variance",
        "raised_by": "user_mgr",
        "assigned_to": "user_aud",
        "status": "open",
    }
    defaults.update(overrides)
    return ReviewNote(**defaults)


def make_user(clerk_user_id: str, **overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "clerk_user_id": clerk_user_id,
        "email": "aud@firm.test",
        "first_name": "Ann",
        "last_name": "Auditor",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def override_db(rows: list[Any]) -> FakeSession:
    session = FakeSession(rows)
    app.dependency_overrides[get_db] = lambda: session
    return session


@pytest.mark.asyncio
async def test_firm_dashboard_summarises_across_engagements() -> None:
    cust = make_client(name="Acme Ltd")
    active = make_engagement(client_id=cust.id, status="review", fiscal_year=2026)
    archived = make_engagement(client_id=cust.id, status="completed", fiscal_year=2025)
    rows: list[Any] = [
        cust,
        active,
        archived,
        make_user("user_aud"),
        # Review queue: prepared paper on the active engagement counts...
        make_paper(active.id, status="prepared", index_ref="A-1"),
        make_paper(active.id, status="approved", index_ref="A-2"),  # done, excluded
        # ...but a prepared paper on the archived engagement does not.
        make_paper(archived.id, status="prepared", index_ref="Z-9"),
        # Overdue procedure on the active engagement counts.
        make_procedure(active.id, due_date=date.today() - timedelta(days=3)),
        # Future / completed procedures excluded.
        make_procedure(active.id, due_date=date.today() + timedelta(days=10)),
        make_procedure(active.id, status="completed", due_date=date.today() - timedelta(days=9)),
        # Open note counts; a cleared one does not.
        make_note(active.id, status="open"),
        make_note(active.id, status="cleared"),
        make_note(archived.id, status="open"),  # archived -> excluded
    ]
    override_db(rows)

    async with client() as ac:
        resp = await ac.get("/api/firm-dashboard", headers=bearer("manager"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["engagements"]["total"] == 2
    assert body["engagements"]["by_status"]["review"] == 1
    assert body["engagements"]["by_status"]["completed"] == 1
    assert body["engagements"]["by_status"]["draft"] == 0

    assert len(body["review_queue"]) == 1
    item = body["review_queue"][0]
    assert item["index_ref"] == "A-1"
    assert item["client_name"] == "Acme Ltd"
    assert item["prepared_by_name"] == "Ann Auditor"

    assert len(body["overdue_procedures"]) == 1
    overdue = body["overdue_procedures"][0]
    assert overdue["days_overdue"] == 3
    assert overdue["assignee_name"] == "Ann Auditor"

    assert body["open_review_notes"] == 1


@pytest.mark.asyncio
async def test_firm_dashboard_empty_returns_zeros() -> None:
    override_db([])

    async with client() as ac:
        resp = await ac.get("/api/firm-dashboard", headers=bearer("partner"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["engagements"]["total"] == 0
    assert body["review_queue"] == []
    assert body["overdue_procedures"] == []
    assert body["open_review_notes"] == 0


@pytest.mark.asyncio
async def test_firm_dashboard_forbidden_for_auditor() -> None:
    override_db([])

    async with client() as ac:
        resp = await ac.get("/api/firm-dashboard", headers=bearer("auditor"))

    assert resp.status_code == 403
