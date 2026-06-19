import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import (
    AuditTrailEntry,
    CompletionChecklistItem,
    Engagement,
    ReviewNote,
    User,
)
from database.session import get_db
from main import app
from services.completion_service import STANDARD_ITEMS
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
        "status": "review",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_item(engagement_id: uuid.UUID, **overrides: Any) -> CompletionChecklistItem:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "item_key": "going_concern",
        "category": "Going concern",
        "title": "Conclude on going concern",
        "isa_reference": "ISA 570",
        "status": "open",
        "note": None,
        "resolved_by": None,
        "resolved_at": None,
        "sort_order": 0,
    }
    defaults.update(overrides)
    return CompletionChecklistItem(**defaults)


def make_note(engagement_id: uuid.UUID, **overrides: Any) -> ReviewNote:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "working_paper_id": None,
        "text": "Tie this to the lead schedule.",
        "raised_by": "user_test",
        "assigned_to": None,
        "status": "open",
        "response": None,
        "responded_by": None,
        "responded_at": None,
        "cleared_by": None,
        "cleared_at": None,
    }
    defaults.update(overrides)
    return ReviewNote(**defaults)


def make_user(clerk_user_id: str = "user_test", **overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "clerk_user_id": clerk_user_id,
        "email": "jane@firm.example",
        "first_name": "Jane",
        "last_name": "Manager",
        "role": "manager",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def base(engagement_id: uuid.UUID) -> str:
    return f"/api/engagements/{engagement_id}/completion-checklist"


def status_url(engagement_id: uuid.UUID) -> str:
    return f"/api/engagements/{engagement_id}/status"


@pytest.mark.unit
async def test_seed_adds_the_standard_library() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(f"{base(engagement.id)}/seed", headers=bearer("manager"))
    assert response.status_code == 201
    items = [r for r in session.added if isinstance(r, CompletionChecklistItem)]
    assert len(items) == len(STANDARD_ITEMS)
    assert {i.status for i in items} == {"open"}


@pytest.mark.unit
async def test_seed_is_idempotent() -> None:
    engagement = make_engagement()
    existing = [
        make_item(engagement.id, item_key=spec["item_key"], title=spec["title"])
        for spec in STANDARD_ITEMS
    ]
    session = FakeSession(rows=[engagement, *existing])
    use_db(session)
    async with client() as c:
        response = await c.post(f"{base(engagement.id)}/seed", headers=bearer("manager"))
    assert response.status_code == 201
    added = [r for r in session.added if isinstance(r, CompletionChecklistItem)]
    assert added == []


@pytest.mark.unit
async def test_auditor_cannot_seed() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(f"{base(engagement.id)}/seed", headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_resolve_item_stamps_resolver() -> None:
    engagement = make_engagement()
    item = make_item(engagement.id)
    user = make_user("user_test")
    session = FakeSession(rows=[engagement, item, user])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{item.id}",
            json={"status": "complete", "note": "No indicators."},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["resolved_by"] == "user_test"
    assert body["resolved_by_name"] == "Jane Manager"
    assert item.resolved_at is not None
    audit = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit and audit[0].action == "update"


@pytest.mark.unit
async def test_readiness_reflects_open_items_and_notes() -> None:
    engagement = make_engagement()
    open_item = make_item(engagement.id, status="open")
    note = make_note(engagement.id, status="open")
    use_db(FakeSession(rows=[engagement, open_item, note]))
    async with client() as c:
        response = await c.get(f"{base(engagement.id)}/readiness", headers=bearer("auditor"))
    body = response.json()
    assert body == {"ready": False, "total_items": 1, "open_items": 1, "uncleared_notes": 1}


@pytest.mark.unit
async def test_readiness_true_when_resolved_and_no_notes() -> None:
    engagement = make_engagement()
    done = make_item(engagement.id, status="complete")
    use_db(FakeSession(rows=[engagement, done]))
    async with client() as c:
        response = await c.get(f"{base(engagement.id)}/readiness", headers=bearer("auditor"))
    assert response.json()["ready"] is True


@pytest.mark.unit
async def test_complete_blocked_by_open_checklist_item() -> None:
    engagement = make_engagement(status="review")
    open_item = make_item(engagement.id, status="open")
    use_db(FakeSession(rows=[engagement, open_item]))
    async with client() as c:
        response = await c.patch(
            status_url(engagement.id), json={"status": "completed"}, headers=bearer("partner")
        )
    assert response.status_code == 409
    assert "checklist" in response.json()["detail"].lower()


@pytest.mark.unit
async def test_complete_blocked_by_uncleared_note() -> None:
    engagement = make_engagement(status="review")
    done = make_item(engagement.id, status="complete")
    note = make_note(engagement.id, status="responded")
    use_db(FakeSession(rows=[engagement, done, note]))
    async with client() as c:
        response = await c.patch(
            status_url(engagement.id), json={"status": "completed"}, headers=bearer("partner")
        )
    assert response.status_code == 409
    assert "review note" in response.json()["detail"].lower()


@pytest.mark.unit
async def test_complete_blocked_when_checklist_not_initialized() -> None:
    engagement = make_engagement(status="review")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.patch(
            status_url(engagement.id), json={"status": "completed"}, headers=bearer("partner")
        )
    assert response.status_code == 409
