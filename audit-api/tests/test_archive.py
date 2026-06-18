import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import (
    CompletionChecklistItem,
    Engagement,
    EngagementArchive,
    User,
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
        "status": "review",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_resolved_item(engagement_id: uuid.UUID) -> CompletionChecklistItem:
    return CompletionChecklistItem(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement_id,
        item_key="going_concern",
        category="Going concern",
        title="Conclude on going concern",
        isa_reference="ISA 570",
        status="complete",
        sort_order=0,
    )


def make_archive(engagement_id: uuid.UUID, **overrides: Any) -> EngagementArchive:
    archived = now()
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": archived,
        "updated_at": archived,
        "engagement_id": engagement_id,
        "archived_by": "user_test",
        "archived_at": archived,
        "retention_years": 7,
        "retention_until": archived.replace(year=archived.year + 7),
        "note": None,
    }
    defaults.update(overrides)
    return EngagementArchive(**defaults)


def make_user(clerk_user_id: str = "user_test", **overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "clerk_user_id": clerk_user_id,
        "email": "pat@firm.example",
        "first_name": "Pat",
        "last_name": "Partner",
        "role": "partner",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


@pytest.mark.unit
async def test_completing_engagement_writes_archive_with_retention() -> None:
    engagement = make_engagement(status="review")
    session = FakeSession(rows=[engagement, make_resolved_item(engagement.id)])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            f"/api/engagements/{engagement.id}/status",
            json={"status": "completed"},
            headers=bearer("partner"),
        )
    assert response.status_code == 200
    archives = [r for r in session.added if isinstance(r, EngagementArchive)]
    assert len(archives) == 1
    archive = archives[0]
    assert archive.retention_years == 7
    assert archive.retention_until.year == archive.archived_at.year + 7


@pytest.mark.unit
async def test_get_archive_returns_record_with_name() -> None:
    engagement = make_engagement(status="completed")
    archive = make_archive(engagement.id)
    use_db(FakeSession(rows=[engagement, archive, make_user("user_test")]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/archive", headers=bearer("auditor")
        )
    assert response.status_code == 200
    body = response.json()
    assert body["retention_years"] == 7
    assert body["archived_by_name"] == "Pat Partner"


@pytest.mark.unit
async def test_get_archive_is_null_when_not_archived() -> None:
    engagement = make_engagement(status="review")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/archive", headers=bearer("auditor")
        )
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.unit
async def test_completed_engagement_blocks_review_note() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            f"/api/engagements/{engagement.id}/review-notes",
            json={"text": "Late note"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409
    assert "read-only" in response.json()["detail"].lower()


@pytest.mark.unit
async def test_completed_engagement_blocks_report_creation() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            f"/api/engagements/{engagement.id}/reports",
            json={"report_type": "audit_report", "opinion_type": "unmodified"},
            headers=bearer("partner"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_completed_engagement_blocks_cross_reference() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            f"/api/engagements/{engagement.id}/cross-references",
            json={
                "source_type": "working_paper",
                "source_id": str(uuid.uuid4()),
                "target_type": "document",
                "target_id": str(uuid.uuid4()),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 409
