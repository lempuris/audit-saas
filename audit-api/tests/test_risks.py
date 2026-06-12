import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, Risk
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client

ASSERTION_RISK: dict[str, Any] = {
    "level": "assertion",
    "fs_area": "revenue",
    "assertions": ["occurrence", "cutoff"],
    "description": "Revenue may be overstated near year end",
    "inherent_rating": "high",
    "control_rating": "medium",
    "is_significant": True,
    "planned_response": "Extended cutoff testing",
}

ENTITY_RISK: dict[str, Any] = {
    "level": "entity",
    "description": "Management override of controls",
    "inherent_rating": "high",
    "control_rating": "high",
    "is_significant": True,
}


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
        "is_significant": False,
        "planned_response": None,
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return Risk(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/risks{suffix}"


@pytest.mark.unit
async def test_auditor_cannot_create() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(url(engagement.id), json=ASSERTION_RISK, headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_create_assertion_risk_derives_combined_rating() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(url(engagement.id), json=ASSERTION_RISK, headers=bearer("manager"))
    assert response.status_code == 201
    body = response.json()
    assert body["combined_rating"] == "high"  # high inherent x medium control
    assert body["assertions"] == ["occurrence", "cutoff"]
    assert body["created_by"] == "user_test"
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_create_entity_risk() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(url(engagement.id), json=ENTITY_RISK, headers=bearer("partner"))
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == "entity"
    assert body["fs_area"] is None
    assert body["combined_rating"] == "high"


@pytest.mark.unit
async def test_high_inherent_low_control_is_medium() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    payload = dict(ASSERTION_RISK, control_rating="low")
    async with client() as c:
        response = await c.post(url(engagement.id), json=payload, headers=bearer("manager"))
    assert response.status_code == 201
    assert response.json()["combined_rating"] == "medium"


@pytest.mark.unit
async def test_assertion_risk_requires_fs_area() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    payload = dict(ASSERTION_RISK)
    del payload["fs_area"]
    async with client() as c:
        response = await c.post(url(engagement.id), json=payload, headers=bearer("manager"))
    assert response.status_code == 422


@pytest.mark.unit
async def test_entity_risk_rejects_fs_area() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    payload = dict(ENTITY_RISK, fs_area="revenue")
    async with client() as c:
        response = await c.post(url(engagement.id), json=payload, headers=bearer("manager"))
    assert response.status_code == 422


@pytest.mark.unit
async def test_list_risks() -> None:
    engagement = make_engagement()
    risk_a = make_risk(engagement.id)
    risk_b = make_risk(engagement.id, level="entity", fs_area=None, assertions=[])
    use_db(FakeSession(rows=[engagement, risk_a, risk_b]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.unit
async def test_update_recomputes_combined_rating() -> None:
    engagement = make_engagement()
    risk = make_risk(engagement.id)
    session = FakeSession(rows=[engagement, risk])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{risk.id}"),
            json={"inherent_rating": "low", "control_rating": "low"},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    assert response.json()["combined_rating"] == "low"
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1
    assert audit_rows[0].before is not None


@pytest.mark.unit
async def test_update_risk_of_other_engagement_is_404() -> None:
    engagement = make_engagement()
    other_risk = make_risk(uuid.uuid4())
    use_db(FakeSession(rows=[engagement, other_risk]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{other_risk.id}"),
            json={"description": "x"},
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_delete_risk_writes_audit_row() -> None:
    engagement = make_engagement()
    risk = make_risk(engagement.id)
    session = FakeSession(rows=[engagement, risk])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{risk.id}"), headers=bearer("manager"))
    assert response.status_code == 204
    assert risk in session.deleted
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "delete"


@pytest.mark.unit
async def test_cannot_modify_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(url(engagement.id), json=ASSERTION_RISK, headers=bearer("partner"))
    assert response.status_code == 409
