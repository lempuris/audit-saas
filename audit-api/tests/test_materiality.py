import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, MaterialityAssessment
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client

VALID_INPUT: dict[str, Any] = {
    "benchmark": "revenue",
    "benchmark_amount": "1000000.00",
    "overall_percentage": "1",
    "performance_percentage": "75",
    "clearly_trivial_percentage": "5",
    "rationale": "Revenue is the most stable benchmark for this entity",
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


def make_assessment(engagement_id: uuid.UUID, **overrides: Any) -> MaterialityAssessment:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "benchmark": "revenue",
        "benchmark_amount": Decimal("1000000.00"),
        "overall_percentage": Decimal("1.00"),
        "overall_materiality": Decimal("10000.00"),
        "performance_percentage": Decimal("75.00"),
        "performance_materiality": Decimal("7500.00"),
        "clearly_trivial_percentage": Decimal("5.00"),
        "clearly_trivial_threshold": Decimal("500.00"),
        "rationale": None,
        "status": "draft",
        "approved_by": None,
        "approved_at": None,
    }
    defaults.update(overrides)
    return MaterialityAssessment(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/materiality{suffix}"


@pytest.mark.unit
async def test_auditor_cannot_write() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.put(url(engagement.id), json=VALID_INPUT, headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_auditor_can_read() -> None:
    engagement = make_engagement()
    assessment = make_assessment(engagement.id)
    use_db(FakeSession(rows=[engagement, assessment]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 200
    assert response.json()["overall_materiality"] == "10000.00"


@pytest.mark.unit
async def test_get_without_assessment_is_404() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("manager"))
    assert response.status_code == 404


@pytest.mark.unit
async def test_create_computes_amounts_and_audits() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.put(url(engagement.id), json=VALID_INPUT, headers=bearer("manager"))
    assert response.status_code == 200
    body = response.json()
    assert body["overall_materiality"] == "10000.00"
    assert body["performance_materiality"] == "7500.00"
    assert body["clearly_trivial_threshold"] == "500.00"
    assert body["status"] == "draft"
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "create"
    assert session.committed


@pytest.mark.unit
async def test_update_replaces_draft_values() -> None:
    engagement = make_engagement()
    assessment = make_assessment(engagement.id)
    session = FakeSession(rows=[engagement, assessment])
    use_db(session)
    updated = dict(VALID_INPUT, benchmark="total_assets", benchmark_amount="2000000.00")
    async with client() as c:
        response = await c.put(url(engagement.id), json=updated, headers=bearer("partner"))
    assert response.status_code == 200
    body = response.json()
    assert body["benchmark"] == "total_assets"
    assert body["overall_materiality"] == "20000.00"
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "update"
    assert audit_rows[0].before is not None


@pytest.mark.unit
async def test_rounding_is_half_up_to_cents() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    payload = dict(
        VALID_INPUT,
        benchmark_amount="333333.33",
        overall_percentage="1.5",
        performance_percentage="66.67",
        clearly_trivial_percentage="5",
    )
    async with client() as c:
        response = await c.put(url(engagement.id), json=payload, headers=bearer("manager"))
    assert response.status_code == 200
    body = response.json()
    # 333,333.33 * 1.5% = 5,000.00 (4,999.99995 rounds half-up)
    assert body["overall_materiality"] == "5000.00"
    assert body["performance_materiality"] == "3333.50"
    assert body["clearly_trivial_threshold"] == "250.00"


@pytest.mark.unit
async def test_cannot_edit_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.put(url(engagement.id), json=VALID_INPUT, headers=bearer("partner"))
    assert response.status_code == 409


@pytest.mark.unit
async def test_cannot_edit_approved_assessment() -> None:
    engagement = make_engagement()
    assessment = make_assessment(
        engagement.id, status="approved", approved_by="user_partner", approved_at=now()
    )
    use_db(FakeSession(rows=[engagement, assessment]))
    async with client() as c:
        response = await c.put(url(engagement.id), json=VALID_INPUT, headers=bearer("manager"))
    assert response.status_code == 409


@pytest.mark.unit
async def test_manager_cannot_approve() -> None:
    engagement = make_engagement()
    assessment = make_assessment(engagement.id)
    use_db(FakeSession(rows=[engagement, assessment]))
    async with client() as c:
        response = await c.post(url(engagement.id, "/approve"), headers=bearer("manager"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_partner_approves_and_locks() -> None:
    engagement = make_engagement()
    assessment = make_assessment(engagement.id)
    session = FakeSession(rows=[engagement, assessment])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/approve"), headers=bearer("partner", sub="user_partner")
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "user_partner"
    assert body["approved_at"] is not None
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1


@pytest.mark.unit
async def test_approve_without_assessment_is_404() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(url(engagement.id, "/approve"), headers=bearer("admin"))
    assert response.status_code == 404


@pytest.mark.unit
async def test_approve_twice_is_409() -> None:
    engagement = make_engagement()
    assessment = make_assessment(
        engagement.id, status="approved", approved_by="user_partner", approved_at=now()
    )
    use_db(FakeSession(rows=[engagement, assessment]))
    async with client() as c:
        response = await c.post(url(engagement.id, "/approve"), headers=bearer("partner"))
    assert response.status_code == 409


@pytest.mark.unit
async def test_reopen_returns_to_draft() -> None:
    engagement = make_engagement()
    assessment = make_assessment(
        engagement.id, status="approved", approved_by="user_partner", approved_at=now()
    )
    session = FakeSession(rows=[engagement, assessment])
    use_db(session)
    async with client() as c:
        response = await c.post(url(engagement.id, "/reopen"), headers=bearer("admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["approved_by"] is None
    assert body["approved_at"] is None


@pytest.mark.unit
async def test_reopen_draft_is_409() -> None:
    engagement = make_engagement()
    assessment = make_assessment(engagement.id)
    use_db(FakeSession(rows=[engagement, assessment]))
    async with client() as c:
        response = await c.post(url(engagement.id, "/reopen"), headers=bearer("partner"))
    assert response.status_code == 409


@pytest.mark.unit
async def test_invalid_percentage_is_422() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    payload = dict(VALID_INPUT, overall_percentage="0")
    async with client() as c:
        response = await c.put(url(engagement.id), json=payload, headers=bearer("manager"))
    assert response.status_code == 422


@pytest.mark.unit
async def test_unknown_engagement_is_404() -> None:
    use_db(FakeSession(rows=[]))
    async with client() as c:
        response = await c.put(url(uuid.uuid4()), json=VALID_INPUT, headers=bearer("manager"))
    assert response.status_code == 404
