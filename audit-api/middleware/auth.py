"""Clerk session-token verification middleware.

Default deny: every request must carry a valid Clerk JWT (RS256, verified
against the instance JWKS) except the paths in PUBLIC_PATHS. On success an
AuthenticatedUser is attached to request.state.user; routers read it via the
get_current_user / require_roles dependencies.

The `role` claim is not in Clerk session tokens by default — it must be added
in the Clerk dashboard (Sessions -> Customize session token) as:
    {"role": "{{user.public_metadata.role}}"}
Tokens without a recognised role still authenticate, but fail every
require_roles() check.
"""

from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from config.settings import get_settings
from models.auth_models import AuthenticatedUser, Role

# /api/health must stay unauthenticated: the ALB target group health checks
# hit it with no credentials.
PUBLIC_PATHS = frozenset({"/api/health"})


class ClerkTokenVerifier:
    """Verifies Clerk RS256 session tokens against the instance JWKS."""

    def __init__(self, jwks_url: str, allowed_azp: list[str]) -> None:
        if not jwks_url:
            raise RuntimeError("CLERK_JWKS_URL is not configured")
        self._jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        self._allowed_azp = allowed_azp

    def verify(self, token: str) -> dict[str, Any]:
        """Return the token's claims. Raises InvalidTokenError if invalid."""
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"require": ["exp", "iat", "sub"]},
            leeway=5,
        )
        # Clerk recommends checking azp (the origin that requested the token)
        # against the list of authorized origins, which for this app is
        # exactly the CORS allowlist (the SPA's origin).
        azp = claims.get("azp")
        if azp is not None and azp not in self._allowed_azp:
            raise InvalidTokenError("azp claim is not an authorized origin")
        return claims


@lru_cache
def get_verifier() -> ClerkTokenVerifier:
    settings = get_settings()
    return ClerkTokenVerifier(settings.clerk_jwks_url, settings.cors_origin_list)


def _user_from_claims(claims: dict[str, Any]) -> AuthenticatedUser:
    role_claim = claims.get("role")
    try:
        role = Role(role_claim) if role_claim else None
    except ValueError:
        role = None
    return AuthenticatedUser(user_id=claims["sub"], session_id=claims.get("sid"), role=role)


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or missing authentication token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _unauthorized()

        try:
            claims = get_verifier().verify(token)
        except PyJWKClientConnectionError:
            # JWKS endpoint unreachable is a server-side fault, not a bad
            # token — propagate to the 500 handler.
            raise
        except (InvalidTokenError, PyJWKClientError):
            return _unauthorized()

        request.state.user = _user_from_claims(claims)
        return await call_next(request)


def get_current_user(request: Request) -> AuthenticatedUser:
    user: AuthenticatedUser | None = getattr(request.state, "user", None)
    if user is None:
        # Only possible if a route is exempted in PUBLIC_PATHS but still
        # declares this dependency — a wiring bug, not a client error.
        raise RuntimeError("get_current_user used on a path the auth middleware does not cover")
    return user


def require_roles(
    *roles: Role,
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Dependency factory: allow only the given roles (default deny)."""

    def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency
