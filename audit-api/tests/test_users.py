import time
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

import middleware.auth as auth_middleware
from database.models import User
from database.session import get_db
from main import app
from middleware.auth import ClerkTokenVerifier
from services.clerk_client import get_clerk_client

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


def make_user(**overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "created_at": datetime.now(UTC),
        "clerk_user_id": "user_abc",
        "email": "asha@firm.example",
        "first_name": "Asha",
        "last_name": "Mushi",
        "role": "auditor",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)


class FakeScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def __iter__(self) -> Any:
        return iter(self._rows)


class FakeSession:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = users or []
        self.added: list[Any] = []
        self.committed = False

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def scalars(self, _query: Any) -> FakeScalarResult:
        return FakeScalarResult(self.users)

    async def commit(self) -> None:
        self.committed = True


class FakeClerk:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def create_invitation(self, email: str, role: str) -> None:
        self.calls.append(("create_invitation", (email, role)))

    async def set_user_role(self, clerk_user_id: str, role: str) -> None:
        self.calls.append(("set_user_role", (clerk_user_id, role)))

    async def ban_user(self, clerk_user_id: str) -> None:
        self.calls.append(("ban_user", (clerk_user_id,)))

    async def unban_user(self, clerk_user_id: str) -> None:
        self.calls.append(("unban_user", (clerk_user_id,)))


@pytest.fixture
def clerk() -> Any:
    fake = FakeClerk()
    app.dependency_overrides[get_clerk_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_clerk_client, None)


def use_db(session: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: session


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def bearer(role: str | None = "admin", sub: str = "user_admin") -> dict[str, str]:
    now = int(time.time())
    claims: dict[str, Any] = {"sub": sub, "iat": now, "exp": now + 600}
    if role:
        claims["role"] = role
    token = jwt.encode(claims, _signing_key, algorithm="RS256")
    return {"Authorization": f"Bearer {token}"}


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
@pytest.mark.parametrize("role", ["partner", "manager", "auditor", None])
async def test_users_endpoints_admin_only(role: str | None) -> None:
    use_db(FakeSession())
    async with client() as c:
        listed = await c.get("/api/users", headers=bearer(role))
        invited = await c.post(
            "/api/users/invitations",
            json={"email": "x@y.z", "role": "auditor"},
            headers=bearer(role),
        )
    assert listed.status_code == 403
    assert invited.status_code == 403


@pytest.mark.unit
async def test_list_users_returns_records() -> None:
    use_db(FakeSession(users=[make_user()]))
    async with client() as c:
        response = await c.get("/api/users", headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["clerk_user_id"] == "user_abc"
    assert body[0]["is_active"] is True


@pytest.mark.unit
async def test_invite_calls_clerk_and_audits(clerk: FakeClerk) -> None:
    session = FakeSession()
    use_db(session)
    async with client() as c:
        response = await c.post(
            "/api/users/invitations",
            json={"email": "new@firm.example", "role": "manager"},
            headers=bearer(),
        )
    assert response.status_code == 204
    assert clerk.calls == [("create_invitation", ("new@firm.example", "manager"))]
    assert len(session.added) == 1
    assert session.added[0].entity_type == "invitation"
    assert session.committed


@pytest.mark.unit
async def test_invalid_role_rejected(clerk: FakeClerk) -> None:
    use_db(FakeSession())
    async with client() as c:
        response = await c.post(
            "/api/users/invitations",
            json={"email": "new@firm.example", "role": "superuser"},
            headers=bearer(),
        )
    assert response.status_code == 422
    assert clerk.calls == []


@pytest.mark.unit
async def test_set_role_updates_local_and_clerk(clerk: FakeClerk) -> None:
    user = make_user()
    session = FakeSession(users=[user])
    use_db(session)
    async with client() as c:
        response = await c.patch(
            "/api/users/user_abc/role", json={"role": "manager"}, headers=bearer()
        )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"
    assert user.role == "manager"
    assert clerk.calls == [("set_user_role", ("user_abc", "manager"))]
    audit = session.added[0]
    assert audit.before == {"role": "auditor"}
    assert audit.after == {"role": "manager"}
    assert session.committed


@pytest.mark.unit
async def test_set_role_unknown_user_404(clerk: FakeClerk) -> None:
    use_db(FakeSession(users=[]))
    async with client() as c:
        response = await c.patch(
            "/api/users/user_missing/role", json={"role": "manager"}, headers=bearer()
        )
    assert response.status_code == 404
    assert clerk.calls == []


@pytest.mark.unit
async def test_deactivate_bans_and_clears_active(clerk: FakeClerk) -> None:
    user = make_user()
    session = FakeSession(users=[user])
    use_db(session)
    async with client() as c:
        response = await c.post("/api/users/user_abc/deactivate", headers=bearer())
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert user.is_active is False
    assert clerk.calls == [("ban_user", ("user_abc",))]
    assert session.committed


@pytest.mark.unit
async def test_reactivate_unbans(clerk: FakeClerk) -> None:
    user = make_user(is_active=False)
    session = FakeSession(users=[user])
    use_db(session)
    async with client() as c:
        response = await c.post("/api/users/user_abc/reactivate", headers=bearer())
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert clerk.calls == [("unban_user", ("user_abc",))]
