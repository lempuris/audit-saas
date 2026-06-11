import time
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

import middleware.auth as auth_middleware
from database.session import get_db
from main import app
from middleware.auth import ClerkTokenVerifier
from models.audit_trail_models import AuditTrailPage
from services import audit_trail_service

ALLOWED_ORIGIN = "http://localhost:3001"

_signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StubJWKSClient:
    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        return SimpleNamespace(key=_signing_key.public_key())


@pytest.fixture(autouse=True)
def _stub_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = ClerkTokenVerifier("https://clerk.test/jwks.json", [ALLOWED_ORIGIN])
    verifier._jwks_client = StubJWKSClient()
    monkeypatch.setattr(auth_middleware, "get_verifier", lambda: verifier)


@pytest.fixture(autouse=True)
def _stub_db() -> Any:
    app.dependency_overrides[get_db] = lambda: object()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def listed(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    async def fake_list_entries(_db: Any, **kwargs: Any) -> AuditTrailPage:
        captured.update(kwargs)
        return AuditTrailPage(total=0, limit=kwargs["limit"], offset=kwargs["offset"], items=[])

    monkeypatch.setattr(audit_trail_service, "list_entries", fake_list_entries)
    return captured


def bearer(role: str | None = None) -> dict[str, str]:
    now = int(time.time())
    claims: dict[str, Any] = {"sub": "user_123", "iat": now, "exp": now + 600}
    if role:
        claims["role"] = role
    token = jwt.encode(claims, _signing_key, algorithm="RS256")
    return {"Authorization": f"Bearer {token}"}


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
def test_record_stages_row_without_commit() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []

        def add(self, instance: Any) -> None:
            self.added.append(instance)

    session = FakeSession()
    entry = audit_trail_service.record(
        session,  # type: ignore[arg-type]
        actor="user_1",
        action="update",
        entity_type="client",
        entity_id="abc",
        before={"name": "Old"},
        after={"name": "New"},
    )
    assert session.added == [entry]
    assert entry.actor_clerk_user_id == "user_1"
    assert entry.before == {"name": "Old"}
    assert entry.after == {"name": "New"}


@pytest.mark.unit
@pytest.mark.parametrize("role", ["auditor", "manager", None])
async def test_viewer_forbidden_for_non_admin_partner(role: str | None) -> None:
    async with client() as c:
        response = await c.get("/api/audit-trail", headers=bearer(role))
    assert response.status_code == 403


@pytest.mark.unit
@pytest.mark.parametrize("role", ["admin", "partner"])
async def test_viewer_allowed_for_admin_and_partner(role: str, listed: dict[str, Any]) -> None:
    async with client() as c:
        response = await c.get(
            "/api/audit-trail",
            params={"entity_type": "client", "limit": 10},
            headers=bearer(role),
        )
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert listed["entity_type"] == "client"
    assert listed["limit"] == 10
    assert listed["offset"] == 0


@pytest.mark.unit
async def test_viewer_requires_token() -> None:
    async with client() as c:
        response = await c.get("/api/audit-trail")
    assert response.status_code == 401
