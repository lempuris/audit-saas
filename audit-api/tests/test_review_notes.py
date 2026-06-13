import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, ReviewNote
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
        "status": "review",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_note(engagement_id: uuid.UUID, **overrides: Any) -> ReviewNote:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "working_paper_id": None,
        "text": "Explain the reconciling item.",
        "raised_by": "user_mgr",
        "assigned_to": "user_test",
        "status": "open",
        "response": None,
        "responded_by": None,
        "responded_at": None,
        "cleared_by": None,
        "cleared_at": None,
    }
    defaults.update(overrides)
    return ReviewNote(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/review-notes{suffix}"


@pytest.mark.unit
async def test_reviewer_raises_note() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={"text": "Explain this", "assigned_to": "user_aud"},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    assert response.json()["status"] == "open"
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_auditor_cannot_raise_note() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(url(engagement.id), json={"text": "x"}, headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_preparer_responds() -> None:
    engagement = make_engagement()
    note = make_note(engagement.id)
    session = FakeSession(rows=[engagement, note])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{note.id}/respond"),
            json={"response": "Cleared to the bank confirmation."},
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "responded"
    assert body["response"] == "Cleared to the bank confirmation."
    assert body["responded_by"] == "user_test"


@pytest.mark.unit
async def test_cannot_respond_to_cleared_note() -> None:
    engagement = make_engagement()
    note = make_note(engagement.id, status="cleared")
    use_db(FakeSession(rows=[engagement, note]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{note.id}/respond"),
            json={"response": "late"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_manager_clears_note() -> None:
    engagement = make_engagement()
    note = make_note(engagement.id, status="responded")
    session = FakeSession(rows=[engagement, note])
    use_db(session)
    async with client() as c:
        response = await c.patch(url(engagement.id, f"/{note.id}/clear"), headers=bearer("manager"))
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"


@pytest.mark.unit
async def test_non_raiser_auditor_cannot_clear() -> None:
    engagement = make_engagement()
    note = make_note(engagement.id, raised_by="someone_else")
    use_db(FakeSession(rows=[engagement, note]))
    async with client() as c:
        response = await c.patch(url(engagement.id, f"/{note.id}/clear"), headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_raiser_can_clear_own_note() -> None:
    engagement = make_engagement()
    # bearer default sub is user_test; make them the raiser.
    note = make_note(engagement.id, raised_by="user_test")
    use_db(FakeSession(rows=[engagement, note]))
    async with client() as c:
        response = await c.patch(url(engagement.id, f"/{note.id}/clear"), headers=bearer("auditor"))
    assert response.status_code == 200


@pytest.mark.unit
async def test_list_filters_by_status() -> None:
    engagement = make_engagement()
    open_note = make_note(engagement.id)
    cleared = make_note(engagement.id, status="cleared")
    use_db(FakeSession(rows=[engagement, open_note, cleared]))
    async with client() as c:
        response = await c.get(url(engagement.id) + "?note_status=open", headers=bearer("manager"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["status"] == "open"


@pytest.mark.unit
async def test_me_review_notes_returns_open_assigned() -> None:
    engagement = make_engagement()
    mine_open = make_note(engagement.id, assigned_to="user_test")
    mine_cleared = make_note(engagement.id, assigned_to="user_test", status="cleared")
    others = make_note(engagement.id, assigned_to="user_other")
    use_db(FakeSession(rows=[engagement, mine_open, mine_cleared, others]))
    async with client() as c:
        response = await c.get("/api/me/review-notes", headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["id"] == str(mine_open.id)
