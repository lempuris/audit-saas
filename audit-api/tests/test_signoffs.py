import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, Signoff, User, WorkingPaper
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
        "status": "fieldwork",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_wp(engagement_id: uuid.UUID, **overrides: Any) -> WorkingPaper:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "fs_area": "cash_and_bank",
        "index_ref": "C-1",
        "title": "Bank reconciliation",
        "objective": "Confirm the year-end bank balance.",
        "result": "",
        "conclusion": "",
        "status": "prepared",
        "procedure_id": None,
        "prepared_by": "user_test",
        "prepared_at": now(),
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return WorkingPaper(**defaults)


def make_user(clerk_user_id: str = "user_test", **overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "clerk_user_id": clerk_user_id,
        "email": "jane@firm.example",
        "first_name": "Jane",
        "last_name": "Partner",
        "role": "partner",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def wp_url(engagement_id: uuid.UUID, wp_id: uuid.UUID) -> str:
    return f"/api/engagements/{engagement_id}/working-papers/{wp_id}/sign-off"


def area_url(engagement_id: uuid.UUID, fs_area: str) -> str:
    return f"/api/engagements/{engagement_id}/fs-areas/{fs_area}/sign-off"


@pytest.mark.unit
async def test_review_prepared_paper_advances_and_records() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="prepared")
    session = FakeSession(rows=[engagement, wp])
    use_db(session)
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "review"}, headers=bearer("manager")
        )
    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "reviewed" and body["resulting_status"] == "reviewed"
    assert wp.status == "reviewed"
    signoffs = [r for r in session.added if isinstance(r, Signoff)]
    assert len(signoffs) == 1 and signoffs[0].target_type == "working_paper"
    audit = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert len(audit) == 1 and audit[0].entity_type == "sign_off"


@pytest.mark.unit
async def test_cannot_review_a_draft_paper() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="draft")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "review"}, headers=bearer("manager")
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_approve_requires_reviewed() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="prepared")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "approve"}, headers=bearer("partner")
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_partner_approves_reviewed_paper() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="reviewed")
    session = FakeSession(rows=[engagement, wp])
    use_db(session)
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "approve"}, headers=bearer("partner")
        )
    assert response.status_code == 201
    assert response.json()["resulting_status"] == "approved"
    assert wp.status == "approved"


@pytest.mark.unit
async def test_manager_cannot_approve() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="reviewed")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "approve"}, headers=bearer("manager")
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_auditor_cannot_sign_off() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="prepared")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "review"}, headers=bearer("auditor")
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_return_sends_paper_back_to_prepared() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="approved")
    session = FakeSession(rows=[engagement, wp])
    use_db(session)
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "return"}, headers=bearer("manager")
        )
    assert response.status_code == 201
    assert response.json()["action"] == "returned"
    assert wp.status == "prepared"


@pytest.mark.unit
async def test_fs_area_review_requires_all_papers_reviewed() -> None:
    engagement = make_engagement()
    reviewed = make_wp(engagement.id, index_ref="C-1", status="reviewed")
    prepared = make_wp(engagement.id, index_ref="C-2", status="prepared")
    use_db(FakeSession(rows=[engagement, reviewed, prepared]))
    async with client() as c:
        response = await c.post(
            area_url(engagement.id, "cash_and_bank"),
            json={"action": "review"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_fs_area_review_succeeds_when_all_reviewed() -> None:
    engagement = make_engagement()
    wp1 = make_wp(engagement.id, index_ref="C-1", status="reviewed")
    wp2 = make_wp(engagement.id, index_ref="C-2", status="approved")
    session = FakeSession(rows=[engagement, wp1, wp2])
    use_db(session)
    async with client() as c:
        response = await c.post(
            area_url(engagement.id, "cash_and_bank"),
            json={"action": "review"},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    signoffs = [r for r in session.added if isinstance(r, Signoff)]
    assert signoffs[0].target_type == "fs_area" and signoffs[0].target_id == "cash_and_bank"


@pytest.mark.unit
async def test_fs_area_return_is_rejected() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            area_url(engagement.id, "cash_and_bank"),
            json={"action": "return"},
            headers=bearer("partner"),
        )
    assert response.status_code == 400


@pytest.mark.unit
async def test_cannot_sign_off_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    wp = make_wp(engagement.id, status="prepared")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            wp_url(engagement.id, wp.id), json={"action": "review"}, headers=bearer("partner")
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_list_sign_offs_resolves_names_and_filters() -> None:
    engagement = make_engagement()
    user = make_user("user_test")
    wp_signoff = Signoff(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        target_type="working_paper",
        target_id=str(uuid.uuid4()),
        action="reviewed",
        resulting_status="reviewed",
        signed_by="user_test",
        note=None,
    )
    area_signoff = Signoff(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        target_type="fs_area",
        target_id="cash_and_bank",
        action="approved",
        resulting_status="approved",
        signed_by="user_test",
        note=None,
    )
    use_db(FakeSession(rows=[engagement, user, wp_signoff, area_signoff]))
    async with client() as c:
        all_rows = await c.get(
            f"/api/engagements/{engagement.id}/sign-offs", headers=bearer("auditor")
        )
        filtered = await c.get(
            f"/api/engagements/{engagement.id}/sign-offs?target_type=fs_area",
            headers=bearer("auditor"),
        )
    assert all_rows.status_code == 200
    assert {r["signed_by_name"] for r in all_rows.json()} == {"Jane Partner"}
    assert len(filtered.json()) == 1 and filtered.json()[0]["target_type"] == "fs_area"


@pytest.mark.unit
async def test_editing_approved_paper_is_blocked() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="approved")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/working-papers/{wp.id}",
            json={"result": "edited"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_status_endpoint_rejects_reviewed() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id, status="prepared")
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/working-papers/{wp.id}/status",
            json={"status": "reviewed"},
            headers=bearer("manager"),
        )
    assert response.status_code == 422
