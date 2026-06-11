"""Thin async client for the Clerk Backend API (api.clerk.com).

User management actions (invite, role change, deactivate) happen in Clerk —
the source of truth for identities — and flow back into the local users table
via the webhook. Clerk 4xx responses surface as 400s with Clerk's message;
5xx/network failures propagate to the 500 handler.
"""

from functools import lru_cache
from typing import Any

import httpx
from fastapi import HTTPException, status

from config.settings import get_settings

CLERK_API_BASE = "https://api.clerk.com/v1"


class ClerkBackendClient:
    def __init__(self, secret_key: str, base_url: str = CLERK_API_BASE) -> None:
        if not secret_key:
            raise RuntimeError("CLERK_SECRET_KEY is not configured")
        self._client = httpx.AsyncClient(
            base_url=base_url, headers={"Authorization": f"Bearer {secret_key}"}, timeout=10
        )

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        response = await self._client.request(method, path, json=json)
        if 400 <= response.status_code < 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Clerk rejected the request: {response.text}",
            )
        response.raise_for_status()
        return response.json() if response.content else None

    async def create_invitation(self, email: str, role: str) -> Any:
        return await self._request(
            "POST",
            "/invitations",
            json={"email_address": email, "public_metadata": {"role": role}},
        )

    async def set_user_role(self, clerk_user_id: str, role: str) -> Any:
        return await self._request(
            "PATCH", f"/users/{clerk_user_id}/metadata", json={"public_metadata": {"role": role}}
        )

    async def ban_user(self, clerk_user_id: str) -> Any:
        return await self._request("POST", f"/users/{clerk_user_id}/ban")

    async def unban_user(self, clerk_user_id: str) -> Any:
        return await self._request("POST", f"/users/{clerk_user_id}/unban")


@lru_cache
def get_clerk_client() -> ClerkBackendClient:
    return ClerkBackendClient(get_settings().clerk_secret_key)
