import base64
import hashlib
import hmac
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Update
from sqlalchemy.dialects import postgresql

from config.settings import get_settings
from database.session import get_db
from main import app
from models.clerk_webhook_models import ClerkUserData
from services.clerk_webhook_service import (
    WebhookVerificationError,
    verify_webhook_signature,
)

_key = b"0" * 32
TEST_SECRET = "whsec_" + base64.b64encode(_key).decode()

WEBHOOK_PATH = "/api/webhooks/clerk"


def sign(body: bytes, *, svix_id: str = "msg_1", timestamp: int | None = None) -> dict[str, str]:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    signed_content = f"{svix_id}.{ts}.".encode() + body
    signature = base64.b64encode(hmac.new(_key, signed_content, hashlib.sha256).digest()).decode()
    return {"svix-id": svix_id, "svix-timestamp": ts, "svix-signature": f"v1,{signature}"}


def user_created_body(**overrides: Any) -> bytes:
    data = {
        "id": "user_abc",
        "first_name": "Asha",
        "last_name": "Mushi",
        "email_addresses": [
            {"id": "em_2", "email_address": "other@firm.example"},
            {"id": "em_1", "email_address": "asha@firm.example"},
        ],
        "primary_email_address_id": "em_1",
        "public_metadata": {"role": "auditor"},
    }
    data.update(overrides)
    return json.dumps({"type": "user.created", "object": "event", "data": data}).encode()


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.committed = False

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def execute(self, statement: Any) -> None:
        self.statements.append(statement)

    async def commit(self) -> None:
        self.committed = True


@pytest.fixture
def db() -> AsyncGenerator[FakeSession, None]:
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "clerk_webhook_secret", TEST_SECRET)


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --- signature verification (pure) ---


@pytest.mark.unit
def test_valid_signature_passes() -> None:
    body = b'{"type":"user.created"}'
    headers = sign(body)
    verify_webhook_signature(
        secret=TEST_SECRET,
        svix_id=headers["svix-id"],
        svix_timestamp=headers["svix-timestamp"],
        svix_signature=headers["svix-signature"],
        body=body,
    )


@pytest.mark.unit
def test_rotated_secret_extra_signatures_pass() -> None:
    body = b"{}"
    headers = sign(body)
    verify_webhook_signature(
        secret=TEST_SECRET,
        svix_id=headers["svix-id"],
        svix_timestamp=headers["svix-timestamp"],
        svix_signature="v1,bm90LXRoZS1yaWdodC1zaWduYXR1cmU= " + headers["svix-signature"],
        body=body,
    )


@pytest.mark.unit
def test_tampered_body_rejected() -> None:
    headers = sign(b'{"a":1}')
    with pytest.raises(WebhookVerificationError):
        verify_webhook_signature(
            secret=TEST_SECRET,
            svix_id=headers["svix-id"],
            svix_timestamp=headers["svix-timestamp"],
            svix_signature=headers["svix-signature"],
            body=b'{"a":2}',
        )


@pytest.mark.unit
def test_stale_timestamp_rejected() -> None:
    body = b"{}"
    stale = int(time.time()) - 3600
    headers = sign(body, timestamp=stale)
    with pytest.raises(WebhookVerificationError):
        verify_webhook_signature(
            secret=TEST_SECRET,
            svix_id=headers["svix-id"],
            svix_timestamp=headers["svix-timestamp"],
            svix_signature=headers["svix-signature"],
            body=body,
        )


@pytest.mark.unit
def test_missing_headers_rejected() -> None:
    with pytest.raises(WebhookVerificationError):
        verify_webhook_signature(
            secret=TEST_SECRET, svix_id="", svix_timestamp="", svix_signature="", body=b"{}"
        )


@pytest.mark.unit
def test_unconfigured_secret_is_server_fault() -> None:
    with pytest.raises(RuntimeError):
        verify_webhook_signature(
            secret="", svix_id="x", svix_timestamp="1", svix_signature="v1,a", body=b"{}"
        )


# --- payload parsing (pure) ---


@pytest.mark.unit
def test_primary_email_resolved_by_id() -> None:
    data = ClerkUserData.model_validate(json.loads(user_created_body())["data"])
    assert data.primary_email == "asha@firm.example"
    assert data.role == "auditor"


@pytest.mark.unit
def test_missing_role_and_email_are_none() -> None:
    data = ClerkUserData.model_validate({"id": "user_x", "public_metadata": {"role": 7}})
    assert data.primary_email is None
    assert data.role is None


# --- endpoint ---


@pytest.mark.unit
async def test_unsigned_request_returns_401(db: FakeSession) -> None:
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=user_created_body())
    assert response.status_code == 401
    assert db.statements == []


@pytest.mark.unit
async def test_bad_signature_returns_401(db: FakeSession) -> None:
    body = user_created_body()
    headers = sign(body)
    headers["svix-signature"] = "v1,aW52YWxpZA=="
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=body, headers=headers)
    assert response.status_code == 401
    assert db.statements == []


@pytest.mark.unit
async def test_user_created_upserts_and_returns_204(db: FakeSession) -> None:
    body = user_created_body()
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=body, headers=sign(body))
    assert response.status_code == 204
    assert len(db.statements) == 1
    assert db.committed
    compiled = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "INSERT INTO users" in compiled
    assert "ON CONFLICT" in compiled
    assert len(db.added) == 1
    assert db.added[0].action == "create"
    assert db.added[0].entity_type == "user"
    assert db.added[0].entity_id == "user_abc"


@pytest.mark.unit
async def test_user_deleted_deactivates(db: FakeSession) -> None:
    body = json.dumps(
        {"type": "user.deleted", "object": "event", "data": {"id": "user_abc", "deleted": True}}
    ).encode()
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=body, headers=sign(body))
    assert response.status_code == 204
    assert len(db.statements) == 1
    assert isinstance(db.statements[0], Update)
    assert db.committed
    assert len(db.added) == 1
    assert db.added[0].action == "delete"


@pytest.mark.unit
async def test_session_created_writes_login_audit_row(db: FakeSession) -> None:
    body = json.dumps(
        {
            "type": "session.created",
            "object": "event",
            "data": {"id": "sess_1", "user_id": "user_abc"},
        }
    ).encode()
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=body, headers=sign(body))
    assert response.status_code == 204
    assert db.statements == []
    assert len(db.added) == 1
    entry = db.added[0]
    assert entry.action == "login"
    assert entry.actor_clerk_user_id == "user_abc"
    assert entry.entity_type == "session"
    assert entry.entity_id == "sess_1"
    assert db.committed


@pytest.mark.unit
async def test_unhandled_event_is_acknowledged_without_writes(db: FakeSession) -> None:
    body = json.dumps({"type": "organization.created", "object": "event", "data": {}}).encode()
    async with client() as c:
        response = await c.post(WEBHOOK_PATH, content=body, headers=sign(body))
    assert response.status_code == 204
    assert db.statements == []
    assert db.added == []
