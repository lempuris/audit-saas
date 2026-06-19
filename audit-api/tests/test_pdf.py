import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import Engagement, EngagementReport
from database.session import get_db
from main import app
from models.reports_models import ReportRecord
from services import pdf_service
from tests.conftest import FakeSession, bearer, client


def now() -> datetime:
    return datetime.now(UTC)


def make_record(**overrides: Any) -> ReportRecord:
    data: dict[str, Any] = {
        "id": uuid.uuid4(),
        "engagement_id": uuid.uuid4(),
        "report_type": "audit_report",
        "opinion_type": "unmodified",
        "title": "Independent Auditor's Report",
        "letterhead": "Kilimanjaro Audit LLP\nArusha, Tanzania",
        "sections": [
            {"key": "opinion", "heading": "Opinion", "body": "In our opinion, the statements…"},
            {"key": "basis", "heading": "Basis for Opinion", "body": "We conducted our audit…"},
        ],
        "status": "draft",
        "created_by": "user_test",
        "created_at": now(),
        "updated_at": now(),
    }
    data.update(overrides)
    return ReportRecord.model_validate(data)


@pytest.mark.unit
def test_html_includes_title_letterhead_and_sections() -> None:
    html = pdf_service.render_report_html(make_record())
    # The apostrophe in the title is HTML-escaped by autoescape, so match a
    # substring without it.
    assert "Independent Auditor" in html
    assert "Kilimanjaro Audit LLP" in html
    assert "Basis for Opinion" in html
    assert "We conducted our audit" in html


@pytest.mark.unit
def test_draft_html_carries_a_draft_flag() -> None:
    assert "DRAFT" in pdf_service.render_report_html(make_record(status="draft"))
    assert "DRAFT" not in pdf_service.render_report_html(make_record(status="final"))


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


def make_report_row(engagement_id: uuid.UUID, **overrides: Any) -> EngagementReport:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "report_type": "audit_report",
        "opinion_type": "unmodified",
        "title": "Independent Auditor's Report",
        "letterhead": "[Firm Name]",
        "sections": [{"key": "opinion", "heading": "Opinion", "body": "…"}],
        "status": "draft",
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return EngagementReport(**defaults)


@pytest.mark.unit
async def test_pdf_endpoint_streams_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    engagement = make_engagement()
    report = make_report_row(engagement.id)
    app.dependency_overrides[get_db] = lambda: FakeSession(rows=[engagement, report])
    # Avoid WeasyPrint's native libraries in the unit suite.
    monkeypatch.setattr(pdf_service, "html_to_pdf", lambda _html: b"%PDF-1.7 fake")

    async with client() as c:
        response = await c.get(
            f"/api/engagements/{engagement.id}/reports/{report.id}/pdf",
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert ".pdf" in response.headers["content-disposition"]


@pytest.mark.integration
def test_real_weasyprint_renders_a_pdf() -> None:
    # Requires WeasyPrint's native libraries; excluded from the default suite.
    pdf = pdf_service.render_report_pdf(make_record())
    assert pdf.startswith(b"%PDF")
