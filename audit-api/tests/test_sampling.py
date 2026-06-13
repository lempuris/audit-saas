import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, Sample
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


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/samples{suffix}"


@pytest.mark.unit
async def test_mus_preview_computes_size() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            json={
                "method": "monetary_unit",
                "population_description": "Revenue invoices",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
                "confidence_level": 95,
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    # n = ceil(1,000,000 * 3.0 / 50,000) = 60
    assert body["sample_size"] == 60
    assert body["reliability_factor"] == "3.00"
    assert len(body["selection_basis"]["selected_monetary_units"]) == 60
    assert "interval" in body["selection_basis"]


@pytest.mark.unit
async def test_random_requires_population_size() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            json={
                "method": "random",
                "population_description": "Invoices",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_random_selection_is_within_population() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            json={
                "method": "random",
                "population_description": "Invoices",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
                "population_size": 200,
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    selected = response.json()["selection_basis"]["selected_items"]
    assert len(selected) == 60
    assert len(set(selected)) == 60  # distinct
    assert all(1 <= i <= 200 for i in selected)


@pytest.mark.unit
async def test_systematic_records_step_and_start() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            json={
                "method": "systematic",
                "population_description": "Invoices",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
                "population_size": 600,
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    basis = response.json()["selection_basis"]
    assert basis["step"] == 10  # 600 // 60
    assert 1 <= basis["random_start"] <= 10


@pytest.mark.unit
async def test_expected_not_below_tolerable_is_422() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/preview"),
            json={
                "method": "monetary_unit",
                "population_description": "x",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
                "expected_misstatement": "50000",
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_create_stores_sample_and_audits() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "method": "monetary_unit",
                "population_description": "Revenue invoices",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["sample_size"] == 60
    samples = [r for r in session.added if isinstance(r, Sample)]
    assert len(samples) == 1
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_create_blocked_on_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "method": "monetary_unit",
                "population_description": "x",
                "population_value": "1000000",
                "tolerable_misstatement": "50000",
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 409
