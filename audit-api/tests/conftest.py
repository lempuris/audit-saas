"""Shared test plumbing: stubbed Clerk JWKS verification, token minting, and
a fake DB session. Older test modules predate this and carry their own copies."""

import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

import middleware.auth as auth_middleware
from main import app
from middleware.auth import ClerkTokenVerifier

ALLOWED_ORIGIN = "http://localhost:3001"

signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _StubJWKSClient:
    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        return SimpleNamespace(key=signing_key.public_key())


@pytest.fixture(autouse=True)
def stub_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = ClerkTokenVerifier("https://clerk.test/jwks.json", [ALLOWED_ORIGIN])
    verifier._jwks_client = _StubJWKSClient()
    monkeypatch.setattr(auth_middleware, "get_verifier", lambda: verifier)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def bearer(role: str | None = None, sub: str = "user_test") -> dict[str, str]:
    now = int(time.time())
    claims: dict[str, Any] = {"sub": sub, "iat": now, "exp": now + 600}
    if role:
        claims["role"] = role
    token = jwt.encode(claims, signing_key, algorithm="RS256")
    return {"Authorization": f"Bearer {token}"}


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class FakeScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def __iter__(self) -> Any:
        return iter(self._rows)


class FakeSession:
    """Records writes; serves canned rows for selects, filtered to the
    entity the query targets (where-clauses are not evaluated — arrange rows
    per test). refresh() fills the server-default timestamp columns the way
    a real flush would."""

    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.committed = False

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def delete(self, instance: Any) -> None:
        self.deleted.append(instance)
        if instance in self.rows:
            self.rows.remove(instance)

    async def scalars(self, query: Any) -> FakeScalarResult:
        try:
            entity = query.column_descriptions[0]["entity"]
        except (AttributeError, IndexError, KeyError, TypeError):
            entity = None
        if entity is None:
            return FakeScalarResult(self.rows)
        return FakeScalarResult([row for row in self.rows if isinstance(row, entity)])

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, instance: Any) -> None:
        now = datetime.now(UTC)
        if getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if getattr(instance, "updated_at", None) is None:
            instance.updated_at = now
