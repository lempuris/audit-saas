import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import (
    AuditTrailEntry,
    Engagement,
    EngagementProcedure,
    ProcedureTemplate,
    Risk,
    RiskProcedureLink,
)
from database.session import get_db
from main import app
from services.procedure_template_seed import SEED_TEMPLATES
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
        "status": "planning",
    }
    defaults.update(overrides)
    return Engagement(**defaults)


def make_template(**overrides: Any) -> ProcedureTemplate:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "fs_area": "revenue",
        "title": "Revenue cutoff testing",
        "description": "Test transactions either side of year end.",
        "isa_reference": "ISA 500",
        "assertions": ["cutoff", "occurrence"],
        "sort_order": 10,
    }
    defaults.update(overrides)
    return ProcedureTemplate(**defaults)


def make_procedure(engagement_id: uuid.UUID, **overrides: Any) -> EngagementProcedure:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": now(),
        "updated_at": now(),
        "engagement_id": engagement_id,
        "template_id": None,
        "fs_area": "revenue",
        "title": "Revenue cutoff testing",
        "description": "Test transactions either side of year end.",
        "isa_reference": "ISA 500",
        "assertions": ["cutoff"],
        "assigned_to": None,
        "status": "not_started",
        "due_date": None,
        "sort_order": 0,
        "created_by": "user_test",
    }
    defaults.update(overrides)
    return EngagementProcedure(**defaults)


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
    return f"/api/engagements/{engagement_id}/procedures{suffix}"


# --- Templates ---


@pytest.mark.unit
async def test_seed_creates_library_once() -> None:
    session = FakeSession(rows=[])
    use_db(session)
    async with client() as c:
        response = await c.post("/api/procedure-templates/seed", headers=bearer("partner"))
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == len(SEED_TEMPLATES)
    assert body["skipped"] == 0
    assert session.committed


@pytest.mark.unit
async def test_seed_skips_existing_titles() -> None:
    existing = make_template(fs_area=SEED_TEMPLATES[0]["fs_area"], title=SEED_TEMPLATES[0]["title"])
    session = FakeSession(rows=[existing])
    use_db(session)
    async with client() as c:
        response = await c.post("/api/procedure-templates/seed", headers=bearer("admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == len(SEED_TEMPLATES) - 1
    assert body["skipped"] == 1


@pytest.mark.unit
async def test_auditor_cannot_seed() -> None:
    use_db(FakeSession(rows=[]))
    async with client() as c:
        response = await c.post("/api/procedure-templates/seed", headers=bearer("auditor"))
    assert response.status_code == 403


@pytest.mark.unit
async def test_create_duplicate_template_is_409() -> None:
    existing = make_template()
    use_db(FakeSession(rows=[existing]))
    async with client() as c:
        response = await c.post(
            "/api/procedure-templates",
            json={
                "fs_area": "revenue",
                "title": "Revenue cutoff testing",
                "description": "dup",
            },
            headers=bearer("manager"),
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_list_templates() -> None:
    use_db(FakeSession(rows=[make_template(), make_template(title="Other", fs_area="tax")]))
    async with client() as c:
        response = await c.get("/api/procedure-templates", headers=bearer("auditor"))
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Engagement procedures ---


@pytest.mark.unit
async def test_add_procedure_from_template_copies_fields() -> None:
    engagement = make_engagement()
    template = make_template()
    session = FakeSession(rows=[engagement, template])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id), json={"template_id": str(template.id)}, headers=bearer("manager")
        )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == template.title
    assert body["fs_area"] == "revenue"
    assert body["template_id"] == str(template.id)
    assert body["status"] == "not_started"
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert len(audit_rows) == 1


@pytest.mark.unit
async def test_add_custom_procedure_requires_fields() -> None:
    engagement = make_engagement()
    use_db(FakeSession(rows=[engagement]))
    async with client() as c:
        response = await c.post(
            url(engagement.id), json={"title": "Only a title"}, headers=bearer("manager")
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_bulk_add_skips_templates_already_on_program() -> None:
    engagement = make_engagement()
    template_a = make_template()
    template_b = make_template(title="Analytical procedures", sort_order=20)
    existing = make_procedure(engagement.id, template_id=template_a.id)
    session = FakeSession(rows=[engagement, template_a, template_b, existing])
    use_db(session)
    async with client() as c:
        response = await c.post(
            url(engagement.id, "/from-templates"), json={}, headers=bearer("manager")
        )
    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["template_id"] == str(template_b.id)


@pytest.mark.unit
async def test_update_assigns_and_sets_due_date() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id)
    session = FakeSession(rows=[engagement, procedure])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{procedure.id}"),
            json={"assigned_to": "user_aud", "due_date": "2026-07-31"},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_to"] == "user_aud"
    assert body["due_date"] == "2026-07-31"


@pytest.mark.unit
async def test_auditor_updates_status_of_own_procedure() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id, assigned_to="user_test")
    session = FakeSession(rows=[engagement, procedure])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{procedure.id}/status"),
            json={"status": "in_progress"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.unit
async def test_auditor_cannot_update_status_of_unassigned_procedure() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id, assigned_to="someone_else")
    use_db(FakeSession(rows=[engagement, procedure]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{procedure.id}/status"),
            json={"status": "completed"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_auditor_cannot_tailor_program() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id, assigned_to="user_test")
    use_db(FakeSession(rows=[engagement, procedure]))
    async with client() as c:
        response = await c.patch(
            url(engagement.id, f"/{procedure.id}"),
            json={"title": "Changed"},
            headers=bearer("auditor"),
        )
    assert response.status_code == 403


@pytest.mark.unit
async def test_link_risks_replaces_set() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id)
    risk_a = make_risk(engagement.id)
    risk_b = make_risk(engagement.id)
    old_link = RiskProcedureLink(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        risk_id=risk_a.id,
        procedure_id=procedure.id,
    )
    session = FakeSession(rows=[engagement, procedure, risk_a, risk_b, old_link])
    use_db(session)
    async with client() as c:
        response = await c.put(
            url(engagement.id, f"/{procedure.id}/risks"),
            json={"risk_ids": [str(risk_b.id)]},
            headers=bearer("manager"),
        )
    assert response.status_code == 200
    assert response.json()["linked_risk_ids"] == [str(risk_b.id)]
    assert old_link in session.deleted
    new_links = [row for row in session.added if isinstance(row, RiskProcedureLink)]
    assert len(new_links) == 1
    assert new_links[0].risk_id == risk_b.id


@pytest.mark.unit
async def test_link_risk_from_other_engagement_is_404() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id)
    foreign_risk = make_risk(uuid.uuid4())
    use_db(FakeSession(rows=[engagement, procedure, foreign_risk]))
    async with client() as c:
        response = await c.put(
            url(engagement.id, f"/{procedure.id}/risks"),
            json={"risk_ids": [str(foreign_risk.id)]},
            headers=bearer("manager"),
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_list_includes_linked_risk_ids() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id)
    risk = make_risk(engagement.id)
    link = RiskProcedureLink(
        id=uuid.uuid4(),
        created_at=now(),
        updated_at=now(),
        risk_id=risk.id,
        procedure_id=procedure.id,
    )
    use_db(FakeSession(rows=[engagement, procedure, risk, link]))
    async with client() as c:
        response = await c.get(url(engagement.id), headers=bearer("auditor"))
    assert response.status_code == 200
    body = response.json()
    assert body[0]["linked_risk_ids"] == [str(risk.id)]


@pytest.mark.unit
async def test_delete_procedure_writes_audit_row() -> None:
    engagement = make_engagement()
    procedure = make_procedure(engagement.id)
    session = FakeSession(rows=[engagement, procedure])
    use_db(session)
    async with client() as c:
        response = await c.delete(url(engagement.id, f"/{procedure.id}"), headers=bearer("manager"))
    assert response.status_code == 204
    assert procedure in session.deleted
    audit_rows = [row for row in session.added if isinstance(row, AuditTrailEntry)]
    assert audit_rows[0].action == "delete"


@pytest.mark.unit
async def test_cannot_modify_completed_engagement() -> None:
    engagement = make_engagement(status="completed")
    template = make_template()
    use_db(FakeSession(rows=[engagement, template]))
    async with client() as c:
        response = await c.post(
            url(engagement.id), json={"template_id": str(template.id)}, headers=bearer("manager")
        )
    assert response.status_code == 409


@pytest.mark.unit
async def test_seed_templates_match_known_fs_areas() -> None:
    from models.trial_balance_models import FSArea

    areas = {str(a) for a in FSArea}
    assert all(entry["fs_area"] in areas for entry in SEED_TEMPLATES)
