import time
from types import SimpleNamespace
from typing import Annotated, Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient

import middleware.auth as auth_middleware
from database.session import get_db
from main import app
from middleware.auth import ClerkTokenVerifier, require_roles
from models.auth_models import AuthenticatedUser, Role

ALLOWED_ORIGIN = "http://localhost:3001"

_signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Test-only role-gated route so require_roles is exercised end-to-end
# through the middleware.
_test_router = APIRouter(prefix="/api/_test")


@_test_router.get("/admin-only")
async def _admin_only(
    user: Annotated[AuthenticatedUser, Depends(require_roles(Role.ADMIN))],
) -> dict[str, str]:
    return {"user_id": user.user_id}


app.include_router(_test_router)


class StubJWKSClient:
    """Stands in for PyJWKClient: always returns the test public key."""

    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        return SimpleNamespace(key=_signing_key.public_key())


@pytest.fixture(autouse=True)
def _stub_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = ClerkTokenVerifier("https://clerk.test/jwks.json", [ALLOWED_ORIGIN])
    verifier._jwks_client = StubJWKSClient()
    monkeypatch.setattr(auth_middleware, "get_verifier", lambda: verifier)


def make_token(
    *,
    sub: str = "user_123",
    expires_in: int = 600,
    key: rsa.RSAPrivateKey | None = None,
    **extra: Any,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {"sub": sub, "iat": now, "exp": now + expires_in, "sid": "sess_abc"}
    claims.update(extra)
    return jwt.encode(claims, key or _signing_key, algorithm="RS256")


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
async def test_me_without_token_returns_401() -> None:
    async with client() as c:
        response = await c.get("/api/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.unit
async def test_me_with_malformed_header_returns_401() -> None:
    async with client() as c:
        response = await c.get("/api/me", headers={"Authorization": "Token abc"})
    assert response.status_code == 401


@pytest.mark.unit
async def test_me_with_garbage_token_returns_401() -> None:
    async with client() as c:
        response = await c.get("/api/me", headers=bearer("not-a-jwt"))
    assert response.status_code == 401


@pytest.mark.unit
async def test_me_with_expired_token_returns_401() -> None:
    async with client() as c:
        response = await c.get("/api/me", headers=bearer(make_token(expires_in=-60)))
    assert response.status_code == 401


@pytest.mark.unit
async def test_me_with_wrong_signature_returns_401() -> None:
    async with client() as c:
        response = await c.get("/api/me", headers=bearer(make_token(key=_other_key)))
    assert response.status_code == 401


@pytest.mark.unit
async def test_me_with_disallowed_azp_returns_401() -> None:
    token = make_token(azp="https://evil.example.com")
    async with client() as c:
        response = await c.get("/api/me", headers=bearer(token))
    assert response.status_code == 401


@pytest.mark.unit
async def test_me_with_valid_token_returns_user() -> None:
    token = make_token(role="partner", azp=ALLOWED_ORIGIN)
    async with client() as c:
        response = await c.get("/api/me", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user_123"
    assert body["session_id"] == "sess_abc"
    assert body["role"] == "partner"


@pytest.mark.unit
async def test_unrecognised_role_maps_to_none() -> None:
    async with client() as c:
        response = await c.get("/api/me", headers=bearer(make_token(role="superuser")))
    assert response.status_code == 200
    assert response.json()["role"] is None


@pytest.mark.unit
async def test_role_gated_route_forbidden_for_other_roles() -> None:
    async with client() as c:
        response = await c.get("/api/_test/admin-only", headers=bearer(make_token(role="auditor")))
    assert response.status_code == 403


@pytest.mark.unit
async def test_role_gated_route_forbidden_without_role() -> None:
    async with client() as c:
        response = await c.get("/api/_test/admin-only", headers=bearer(make_token()))
    assert response.status_code == 403


@pytest.mark.unit
async def test_role_gated_route_allowed_for_admin() -> None:
    async with client() as c:
        response = await c.get("/api/_test/admin-only", headers=bearer(make_token(role="admin")))
    assert response.status_code == 200


@pytest.mark.unit
async def test_health_stays_public() -> None:
    class FakeResult:
        def scalar_one(self) -> int:
            return 1

    class FakeSession:
        async def execute(self, _query: object) -> FakeResult:
            return FakeResult()

    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        async with client() as c:
            response = await c.get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
