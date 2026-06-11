import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from database.models import Client
from database.session import get_db
from main import app
from tests.conftest import FakeSession, bearer, client


def make_client_row(**overrides: Any) -> Client:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "name": "Kilimanjaro Traders Ltd",
        "industry": "Retail",
        "risk_rating": "medium",
        "contacts": [{"name": "Neema J", "position": "CFO", "email": "cfo@kt.example"}],
        "archived": False,
    }
    defaults.update(overrides)
    return Client(**defaults)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


@pytest.mark.unit
async def test_reads_allowed_for_all_roles_writes_gated() -> None:
    use_db(FakeSession())
    async with client() as c:
        read = await c.get("/api/clients", headers=bearer("auditor"))
        write = await c.post("/api/clients", json={"name": "X"}, headers=bearer("auditor"))
        archive = await c.delete(f"/api/clients/{uuid.uuid4()}", headers=bearer("manager"))
    assert read.status_code == 200
    assert write.status_code == 403
    assert archive.status_code == 403


@pytest.mark.unit
async def test_unauthenticated_rejected() -> None:
    use_db(FakeSession())
    async with client() as c:
        response = await c.get("/api/clients")
    assert response.status_code == 401


@pytest.mark.unit
async def test_create_client_writes_audit_row() -> None:
    session = FakeSession()
    use_db(session)
    payload = {
        "name": "Serengeti Mills",
        "industry": "Manufacturing",
        "risk_rating": "high",
        "contacts": [{"name": "Ali H", "email": "ali@sm.example"}],
    }
    async with client() as c:
        response = await c.post("/api/clients", json=payload, headers=bearer("manager"))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Serengeti Mills"
    assert body["risk_rating"] == "high"
    assert body["contacts"][0]["name"] == "Ali H"
    # one Client + one audit row staged, committed together
    types = {type(obj).__name__ for obj in session.added}
    assert types == {"Client", "AuditTrailEntry"}
    audit = next(o for o in session.added if type(o).__name__ == "AuditTrailEntry")
    assert audit.action == "create"
    assert audit.entity_type == "client"
    assert audit.after["name"] == "Serengeti Mills"
    assert session.committed


@pytest.mark.unit
async def test_invalid_risk_rating_rejected() -> None:
    use_db(FakeSession())
    async with client() as c:
        response = await c.post(
            "/api/clients",
            json={"name": "X", "risk_rating": "extreme"},
            headers=bearer("manager"),
        )
    assert response.status_code == 422


@pytest.mark.unit
async def test_update_records_before_and_after() -> None:
    row = make_client_row()
    session = FakeSession(rows=[row])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            f"/api/clients/{row.id}",
            json={"risk_rating": "high"},
            headers=bearer("partner"),
        )
    assert response.status_code == 200
    assert response.json()["risk_rating"] == "high"
    assert row.risk_rating == "high"
    audit = session.added[0]
    assert audit.action == "update"
    assert audit.before["risk_rating"] == "medium"
    assert audit.after["risk_rating"] == "high"
    assert session.committed


@pytest.mark.unit
async def test_update_unknown_client_404() -> None:
    use_db(FakeSession(rows=[]))
    async with client() as c:
        response = await c.patch(
            f"/api/clients/{uuid.uuid4()}", json={"name": "Y"}, headers=bearer("admin")
        )
    assert response.status_code == 404


@pytest.mark.unit
async def test_delete_archives_instead_of_removing() -> None:
    row = make_client_row()
    session = FakeSession(rows=[row])
    use_db(session)
    async with client() as c:
        response = await c.delete(f"/api/clients/{row.id}", headers=bearer("partner"))
    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert row.archived is True
    audit = session.added[0]
    assert audit.action == "delete"
    assert audit.before["archived"] is False
    assert audit.after["archived"] is True


@pytest.mark.unit
async def test_list_serializes_rows() -> None:
    use_db(FakeSession(rows=[make_client_row()]))
    async with client() as c:
        response = await c.get("/api/clients", headers=bearer("partner"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Kilimanjaro Traders Ltd"
    assert body[0]["contacts"][0]["position"] == "CFO"
