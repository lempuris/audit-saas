import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import AuditTrailEntry, Engagement, EngagementReport
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


def make_report(engagement_id: uuid.UUID, **overrides: Any) -> EngagementReport:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "report_type": "audit_report",
        "opinion_type": "unmodified",
        "title": "Independent Auditor's Report",
        "letterhead": "[Firm Name]",
        "sections": [{"key": "opinion", "heading": "Opinion", "body": "..."}],
        "status": "draft",
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return EngagementReport(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def base(engagement_id: uuid.UUID) -> str:
    return f"/api/engagements/{engagement_id}/reports"


@pytest.mark.unit
async def test_create_unmodified_audit_report_seeds_sections() -> None:
    engagement = make_engagement()
    session = FakeSession(rows=[engagement])
    use_db(session)
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "audit_report", "opinion_type": "unmodified"},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    headings = {s["heading"] for s in body["sections"]}
    assert "Opinion" in headings
    assert "Auditor's Responsibilities for the Audit of the Financial Statements" in headings
    audit = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit and audit[0].action == "create"


@pytest.mark.unit
async def test_create_qualified_uses_qualified_basis_wording() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "audit_report", "opinion_type": "qualified"},
            headers=bearer("partner"),
        )
    sections = {s["key"]: s for s in response.json()["sections"]}
    assert sections["basis_for_opinion"]["heading"] == "Basis for Qualified Opinion"
    assert "qualified opinion" in sections["basis_for_opinion"]["body"]


@pytest.mark.unit
async def test_create_management_letter_seeds_its_sections() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "management_letter"},
            headers=bearer("manager"),
        )
    assert response.status_code == 201
    keys = {s["key"] for s in response.json()["sections"]}
    assert "recommendations" in keys and "opinion" not in keys


@pytest.mark.unit
async def test_audit_report_requires_opinion_type() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "audit_report"},
            headers=bearer("manager"),
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_duplicate_report_type_is_409() -> None:
    engagement = make_engagement()
    existing = make_report(engagement.id, report_type="audit_report")
    use_db(FakeSession(rows=[engagement, existing]))
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "audit_report", "opinion_type": "adverse"},
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_auditor_cannot_create() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            base(engagement.id),
            json={"report_type": "audit_report", "opinion_type": "unmodified"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_manager_edits_sections_and_title() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id)
    session = FakeSession(rows=[engagement, report])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={
                "title": "Auditor's Report (revised)",
                "sections": [{"key": "opinion", "heading": "Opinion", "body": "Edited body."}],
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Auditor's Report (revised)"
    assert body["sections"][0]["body"] == "Edited body."


@pytest.mark.unit
async def test_changing_opinion_regenerates_opinion_sections() -> None:
    engagement = make_engagement()
    report = make_report(
        engagement.id,
        opinion_type="unmodified",
        sections=[
            {"key": "opinion", "heading": "Opinion", "body": "the firm's opinion body"},
            {
                "key": "basis_for_opinion",
                "heading": "Basis for Opinion",
                "body": "the firm's basis",
            },
            {"key": "signature", "heading": "Signature", "body": "kept as edited"},
        ],
    )
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={"opinion_type": "adverse"},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["opinion_type"] == "adverse"
    sections = {s["key"]: s for s in body["sections"]}
    # The Opinion and Basis for Opinion sections are regenerated (heading and
    # body) to the standard ISA wording for the new opinion.
    assert sections["opinion"]["heading"] == "Adverse Opinion"
    assert "do not present fairly" in sections["opinion"]["body"]
    assert sections["basis_for_opinion"]["heading"] == "Basis for Adverse Opinion"
    assert sections["basis_for_opinion"]["body"] != "the firm's basis"
    # Non-opinion sections keep the firm's edits.
    assert sections["signature"]["body"] == "kept as edited"


@pytest.mark.unit
async def test_changing_opinion_on_management_letter_is_400() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id, report_type="management_letter", opinion_type=None)
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={"opinion_type": "qualified"},
            headers=bearer("manager"),
        )
    assert response.status_code == 400


@pytest.mark.unit
async def test_manager_cannot_finalize() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id)
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={"status": "final"},
            headers=bearer("manager"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_partner_finalizes() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id)
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={"status": "final"},
            headers=bearer("partner"),
        )
    assert response.status_code == 200
    assert response.json()["status"] == "final"


@pytest.mark.unit
async def test_finalized_report_locked_to_manager() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id, status="final")
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        response = await c.patch(
            f"{base(engagement.id)}/{report.id}",
            json={"title": "Tweak"},
            headers=bearer("manager"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_only_partner_can_delete() -> None:
    engagement = make_engagement()
    report = make_report(engagement.id)
    use_db(FakeSession(rows=[engagement, report]))
    async with client() as c:
        as_manager = await c.delete(f"{base(engagement.id)}/{report.id}", headers=bearer("manager"))
    assert as_manager.status_code == 403

    session = FakeSession(rows=[engagement, report])
    use_db(session)
    async with client() as c:
        as_partner = await c.delete(f"{base(engagement.id)}/{report.id}", headers=bearer("partner"))
    assert as_partner.status_code == 204
    assert report in session.deleted
