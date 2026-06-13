import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from database.models import (
    AuditTrailEntry,
    CrossReference,
    Engagement,
    TrialBalance,
    TrialBalanceLine,
    WorkingPaper,
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


def make_tb(engagement_id: uuid.UUID, **overrides: Any) -> TrialBalance:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "source_filename": "tb.csv",
        "imported_by": "user_test",
    }
    defaults.update(overrides)
    return TrialBalance(**defaults)


def make_line(trial_balance_id: uuid.UUID, **overrides: Any) -> TrialBalanceLine:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "trial_balance_id": trial_balance_id,
        "account_code": "1000",
        "account_name": "Cash at bank",
        "balance": Decimal("100.00"),
        "prior_year_balance": None,
        "fs_area": "cash_and_bank",
    }
    defaults.update(overrides)
    return TrialBalanceLine(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


def url(engagement_id: uuid.UUID, suffix: str = "") -> str:
    return f"/api/engagements/{engagement_id}/cross-references{suffix}"


@pytest.mark.unit
async def test_create_links_wp_to_tb_line_with_labels() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    tb = make_tb(engagement.id)
    line = make_line(tb.id)
    session = FakeSession(rows=[engagement, wp, tb, line])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "source_type": "working_paper",
                "source_id": str(wp.id),
                "target_type": "trial_balance_line",
                "target_id": str(line.id),
            },
            headers=bearer("auditor"),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["source_label"] == "C-1 Bank rec"
    assert body["target_label"] == "1000 Cash at bank"
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "create"


@pytest.mark.unit
async def test_create_with_missing_target_is_404() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "source_type": "working_paper",
                "source_id": str(wp.id),
                "target_type": "document",
                "target_id": str(uuid.uuid4()),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_self_reference_is_422() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    use_db(FakeSession(rows=[engagement, wp]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "source_type": "working_paper",
                "source_id": str(wp.id),
                "target_type": "working_paper",
                "target_id": str(wp.id),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_duplicate_is_409() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    tb = make_tb(engagement.id)
    line = make_line(tb.id)
    existing = CrossReference(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        source_type="working_paper",
        source_id=wp.id,
        target_type="trial_balance_line",
        target_id=line.id,
        label=None,
        created_by="user_test",
    )
    use_db(FakeSession(rows=[engagement, wp, tb, line, existing]))
    async with client() as c:
        response = await c.post(
            url(engagement.id),
            json={
                "source_type": "working_paper",
                "source_id": str(wp.id),
                "target_type": "trial_balance_line",
                "target_id": str(line.id),
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_list_filters_by_source() -> None:
    engagement = make_engagement()
    wp = make_wp(engagement.id)
    tb = make_tb(engagement.id)
    line = make_line(tb.id)
    ref = CrossReference(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        source_type="working_paper",
        source_id=wp.id,
        target_type="trial_balance_line",
        target_id=line.id,
        label=None,
        created_by="user_test",
    )
    use_db(FakeSession(rows=[engagement, wp, tb, line, ref]))
    async with client() as c:
        response = await c.get(
            url(engagement.id) + f"?source_type=working_paper&source_id={wp.id}",
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["target_label"] == "1000 Cash at bank"


@pytest.mark.unit
async def test_delete_writes_audit_row() -> None:
    engagement = make_engagement()
    ref = CrossReference(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        engagement_id=engagement.id,
        source_type="working_paper",
        source_id=uuid.uuid4(),
        target_type="document",
        target_id=uuid.uuid4(),
        label=None,
        created_by="user_test",
    )
    session = FakeSession(rows=[engagement, ref])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{ref.id}"), headers=bearer("auditor"))
    assert response.status_code == 204
    assert ref in session.deleted
    audit_rows = [r for r in session.added if isinstance(r, AuditTrailEntry)]
    assert audit_rows[0].action == "delete"
