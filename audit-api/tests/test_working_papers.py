import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import (
    AuditTrailEntry,
    Engagement,
    User,
    WorkingPaper,
    WorkingPaperVersion,
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
        "status": "draft",
        "procedure_id": None,
        "prepared_by": None,
        "prepared_at": None,
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return WorkingPaper(**defaults)


def make_version(wp_id: uuid.UUID, version_no: int, **overrides: Any) -> WorkingPaperVersion:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "working_paper_id": wp_id,
        "version_no": version_no,
        "index_ref": "C-1",
        "fs_area": "cash_and_bank",
        "title": "Bank reconciliation",
        "objective": "Confirm the year-end bank balance.",
        "result": "",
        "conclusion": "",
        "status": "draft",
        "edited_by": "user_test",
    }
    defaults.update(overrides)
    return WorkingPaperVersion(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/working-papers{suffix}"


@pytest.mark.unit
async def test_create_working_paper_appends_first_version() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "fs_area": "cash_and_bank",
                "index_ref": "C-1",
                "title": "Bank reconciliation",
                "objective": "Confirm the year-end bank balance.",
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["current_version"] == 1
    versions = [r for r in session.added if isinstance(r, WorkingPaperVersion)]
    assert len(versions) == 1 and versions[0].version_no == 1
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert len(audit_rows) == 1 and audit_rows[0].action == "create"


@pytest.mark.unit
async def test_create_duplicate_index_ref_is_409() -> None:
    engagement = make_engagement()
    existing = make_wp(engagement.id, index_ref="C-1")
    use_db(FakeSession(rows=[engagement, existing]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={"fs_area": "cash_and_bank", "index_ref": "C-1", "title": "Dup"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_update_appends_next_version() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    v1 = make_version(wp.id, 1)
    session = FakeSession(rows=[engagement, wp, v1])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{wp.id}"),
            json={"result": "No reconciling items over the threshold."},
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "No reconciling items over the threshold."
    assert body["current_version"] == 2
    new_versions = [r for r in session.added if isinstance(r, WorkingPaperVersion)]
    assert len(new_versions) == 1 and new_versions[0].version_no == 2


@pytest.mark.unit
async def test_status_to_prepared_stamps_preparer() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    session = FakeSession(rows=[engagement, wp, make_version(wp.id, 1)])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{wp.id}/status"),
            json={"status": "prepared"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "prepared"
    assert body["prepared_by"] == "user_test"
    assert body["prepared_at"] is not None


@pytest.mark.unit
async def test_list_reports_current_version() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    use_db(FakeSession(rows=[engagement, wp, make_version(wp.id, 1), make_version(wp.id, 2)]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["current_version"] == 2


@pytest.mark.unit
async def test_list_versions_sorted() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    use_db(FakeSession(rows=[engagement, wp, make_version(wp.id, 2), make_version(wp.id, 1)]))
    async with client() as c:
        response = await c.get(url(engagement.id, f"/{wp.id}/versions"), headers=bearer("partner"))
    assert response.status_code == 200
    body = response.json()
    assert [v["version_no"] for v in body] == [1, 2]


@pytest.mark.unit
async def test_auditor_cannot_delete() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{wp.id}"), headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_manager_deletes_writes_audit_row() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    session = FakeSession(rows=[engagement, wp])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{wp.id}"), headers=bearer("manager"))
    assert response.status_code == 204
    assert wp in session.deleted
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "delete"


@pytest.mark.unit
async def test_cannot_modify_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={"fs_area": "cash_and_bank", "index_ref": "C-1", "title": "x"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


def make_user(clerk_user_id: str, **overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "clerk_user_id": clerk_user_id,
        "email": "jane@firm.example",
        "first_name": "Jane",
        "last_name": "Auditor",
        "role": "auditor",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


@pytest.mark.unit
async def test_resolves_preparer_and_editor_names() -> None:
    engagement = make_engagement()
    user = make_user("user_test")
    wp = make_wp(engagement.id, status="prepared", prepared_by="user_test")
    version = make_version(wp.id, 1, edited_by="user_test")
    use_db(FakeSession(rows=[engagement, user, wp, version]))
    async with client() as c:
        listing = await c.get(url(engagement.id), headers=bearer("auditor"))
        versions = await c.get(url(engagement.id, f"/{wp.id}/versions"), headers=bearer("auditor"))
    assert listing.json()[0]["prepared_by_name"] == "Jane Auditor"
    assert versions.json()[0]["edited_by_name"] == "Jane Auditor"


@pytest.mark.unit
async def test_working_paper_from_other_engagement_is_404() -> None:
    engagement = make_engagement()
    wp = make_wp(uuid.uuid4())
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.get(url(engagement.id, f"/{wp.id}"), headers=bearer("auditor"))
    assert response.status_code == 404
