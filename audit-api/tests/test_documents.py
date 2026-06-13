import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Document, Engagement, WorkingPaper
from database.session import get_db
from main import app
from services import s3_client
from tests.conftest import FakeSession, bearer, client


def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture(autouse=True)
def stub_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3_client, "presigned_put", lambda key, ct: f"https://s3.test/put/{key}")
    monkeypatch.setattr(s3_client, "presigned_get", lambda key, fn: f"https://s3.test/get/{key}")
    monkeypatch.setattr(s3_client, "head", lambda key: {"size_bytes": 1234, "version_id": "v-abc"})
    monkeypatch.setattr(s3_client, "delete", lambda key: None)


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
        "title": "Bank rec",
        "objective": "x",
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


def make_doc(engagement_id: uuid.UUID, **overrides: Any) -> Document:
    doc_id = overrides.get("id", uuid.uuid4())
    defaults: dict[str, Any] = {
        "id": doc_id,
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "working_paper_id": None,
        "filename": "bank-statement.pdf",
        "content_type": "application/pdf",
        "size_bytes": None,
        "s3_key": f"engagements/{engagement_id}/documents/{doc_id}/bank-statement.pdf",
        "s3_version_id": None,
        "status": "pending",
        "uploaded_by": "user_test",
    }
    defaults.update(overrides)
    return Document(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/documents{suffix}"


@pytest.mark.unit
async def test_presign_creates_pending_document() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/presign-upload"),
            json={"filename": "bank-statement.pdf", "content_type": "application/pdf"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["upload_url"].startswith("https://s3.test/put/")
    docs = [r for r in session.added if isinstance(r, Document)]
    assert len(docs) == 1 and docs[0].status == "pending"


@pytest.mark.unit
async def test_presign_with_foreign_working_paper_is_404() -> None:
    engagement = make_engagement()
    foreign_wp = make_wp(uuid.uuid4())
    use_db(FakeSession(rows=[engagement, foreign_wp]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/presign-upload"),
            json={
                "filename": "f.pdf",
                "content_type": "application/pdf",
                "working_paper_id": str(foreign_wp.id),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_confirm_marks_available_and_logs_create() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id)
    session = FakeSession(rows=[engagement, doc])
    use_db(session)
    async with client() as c:
        response = await c.post(url(engagement.id, f"/{doc.id}/confirm"), headers=bearer("auditor"))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "available"
    assert body["size_bytes"] == 1234
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_download_returns_url_and_logs_read() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id, status="available", size_bytes=10)
    session = FakeSession(rows=[engagement, doc])
    use_db(session)
    async with client() as c:
        response = await c.get(url(engagement.id, f"/{doc.id}/download"), headers=bearer("auditor"))
    assert response.status_code == 200
    assert response.json()["download_url"].startswith("https://s3.test/get/")
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "read"


@pytest.mark.unit
async def test_download_pending_is_409() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id, status="pending")
    use_db(FakeSession(rows=[engagement, doc]))
    async with client() as c:
        response = await c.get(url(engagement.id, f"/{doc.id}/download"), headers=bearer("auditor"))
    assert response.status_code == 409


@pytest.mark.unit
async def test_uploader_can_delete() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id, status="available", uploaded_by="user_test")
    session = FakeSession(rows=[engagement, doc])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{doc.id}"), headers=bearer("auditor"))
    assert response.status_code == 204
    assert doc in session.deleted


@pytest.mark.unit
async def test_non_uploader_auditor_cannot_delete() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id, status="available", uploaded_by="someone_else")
    use_db(FakeSession(rows=[engagement, doc]))
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{doc.id}"), headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_manager_can_delete_others_document() -> None:
    engagement = make_engagement()
    doc = make_doc(engagement.id, status="available", uploaded_by="someone_else")
    session = FakeSession(rows=[engagement, doc])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{doc.id}"), headers=bearer("manager"))
    assert response.status_code == 204


@pytest.mark.unit
async def test_presign_blocked_on_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/presign-upload"),
            json={"filename": "f.pdf", "content_type": "application/pdf"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409
