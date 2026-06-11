import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import Client, Engagement, EngagementTeamMember
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client


def now() -> datetime:
    return datetime.now(UTC)


def make_client_row(**overrides: Any) -> Client:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "name": "Kilimanjaro Traders Ltd",
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
        "status": "draft",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_member(engagement_id: uuid.UUID, **overrides: Any) -> EngagementTeamMember:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "clerk_user_id": "user_member",
        "role_on_engagement": "staff",
        "independence_confirmed": False,
        "independence_confirmed_at": None,
    }
    defaults.update(overrides)
    return EngagementTeamMember(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


@pytest.mark.unit
async def test_auditor_cannot_create_engagement() -> None:
    use_db(FakeSession())
    async with client() as c:
        response = await c.post(
            "/api/engagements",
            json={"client_id": str(uuid.uuid4()), "engagement_type": "audit", "fiscal_year": 2026},
            headers=bearer("auditor"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_create_requires_existing_unarchived_client() -> None:
    archived = make_client_row(archived=True)
    use_db(FakeSession(rows=[archived]))
    async with client() as c:
        response = await c.post(
            "/api/engagements",
            json={"client_id": str(archived.id), "engagement_type": "audit", "fiscal_year": 2026},
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_create_engagement_starts_in_draft_with_audit_row() -> None:
    client_row = make_client_row()
    session = FakeSession(rows=[client_row])
    use_db(session)
    async with client() as c:
        response = await c.post(
            "/api/engagements",
            json={
                "client_id": str(client_row.id),
                "engagement_type": "audit",
                "fiscal_year": 2026,
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    audit = next(o for o in session.added if type(o).__name__ == "AuditTrailEntry")
    assert audit.entity_type == "engagement"
    assert audit.action == "create"
    assert session.committed


@pytest.mark.unit
async def test_valid_transition_draft_to_planning() -> None:
    engagement = make_engagement(status="draft")
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "planning"},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    assert engagement.status == "planning"


@pytest.mark.unit
async def test_skipping_workflow_steps_rejected() -> None:
    engagement = make_engagement(status="draft")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "fieldwork"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409
    assert engagement.status == "draft"


@pytest.mark.unit
async def test_fieldwork_blocked_without_team() -> None:
    engagement = make_engagement(status="planning")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "fieldwork"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409
    assert "team" in response.json()["detail"]


@pytest.mark.unit
async def test_fieldwork_blocked_until_independence_confirmed() -> None:
    engagement = make_engagement(status="planning")
    member = make_member(engagement.id, independence_confirmed=False)
    use_db(FakeSession(rows=[engagement, member]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "fieldwork"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409
    assert "independence" in response.json()["detail"]


@pytest.mark.unit
async def test_fieldwork_allowed_once_team_confirmed() -> None:
    engagement = make_engagement(status="planning")
    member = make_member(
        engagement.id, independence_confirmed=True, independence_confirmed_at=now()
    )
    use_db(FakeSession(rows=[engagement, member]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "fieldwork"},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    assert engagement.status == "fieldwork"


@pytest.mark.unit
async def test_only_partner_or_admin_can_complete() -> None:
    engagement = make_engagement(status="review")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        as_manager = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "completed"},
            headers=bearer("manager"),
        )
    assert as_manager.status_code == 403
    assert engagement.status == "review"

    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        as_partner = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "completed"},
            headers=bearer("partner"),
        )
    assert as_partner.status_code == 200
    assert engagement.status == "completed"


@pytest.mark.unit
async def test_add_team_member_and_duplicate_rejected() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        first = await c.post(
            f"/api/engagements/{engagement.id}/team",
            json={"clerk_user_id": "user_new", "role_on_engagement": "staff"},
            headers=bearer("manager"),
        )
    assert first.status_code == 201
    assert first.json()["independence_confirmed"] is False

    existing = make_member(engagement.id, clerk_user_id="user_new")
    use_db(FakeSession(rows=[engagement, existing]))
    async with client() as c:
        duplicate = await c.post(
            f"/api/engagements/{engagement.id}/team",
            json={"clerk_user_id": "user_new"},
            headers=bearer("manager"),
        )
    assert duplicate.status_code == 409


@pytest.mark.unit
async def test_remove_team_member() -> None:
    engagement = make_engagement()
    member = make_member(engagement.id, clerk_user_id="user_gone")
    session = FakeSession(rows=[engagement, member])
    use_db(session)
    async with client() as c:
        response = await c.delete(
            f"/api/engagements/{engagement.id}/team/user_gone", headers=bearer("manager")
        )
    assert response.status_code == 204
    assert session.deleted == [member]


@pytest.mark.unit
async def test_confirm_independence_requires_membership() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            f"/api/engagements/{engagement.id}/team/confirm-independence",
            headers=bearer("auditor", sub="user_outsider"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_confirm_independence_stamps_member() -> None:
    engagement = make_engagement()
    member = make_member(engagement.id, clerk_user_id="user_me")
    session = FakeSession(rows=[engagement, member])
    use_db(session)
    async with client() as c:
        response = await c.post(
            f"/api/engagements/{engagement.id}/team/confirm-independence",
            headers=bearer("auditor", sub="user_me"),
        )
    assert response.status_code == 200
    assert response.json()["independence_confirmed"] is True
    assert member.independence_confirmed is True
    assert member.independence_confirmed_at is not None


@pytest.mark.unit
async def test_detail_includes_team() -> None:
    engagement = make_engagement()
    member = make_member(engagement.id)
    use_db(FakeSession(rows=[engagement, member]))
    async with client() as c:
        response = await c.get(f"/api/engagements/{engagement.id}", headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert len(body["team"]) == 1
    assert body["team"][0]["clerk_user_id"] == "user_member"
