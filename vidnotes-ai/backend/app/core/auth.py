"""Who is making the request: verifies Supabase Auth access tokens.

Supabase signs access tokens with an asymmetric key (ES256/RS256) and
publishes the public keys at <project>/auth/v1/.well-known/jwks.json, so the
backend can verify tokens itself without any secret. Projects still on the
legacy shared-secret (HS256) keys are verified by asking the Auth server,
as Supabase recommends.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import AppError, ExternalServiceError
from app.models.types import LOCAL_USER_ID

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALGORITHMS = {"ES256", "RS256", "EdDSA"}
# Verified legacy tokens are cached briefly so polling does not call the Auth
# server on every request.
_LEGACY_CACHE_SECONDS = 60
_legacy_cache: dict[str, tuple[float, dict]] = {}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    provider: str | None = None


LOCAL_USER = CurrentUser(id=LOCAL_USER_ID, full_name="Local user", provider="local")


def _sign_in_again() -> AppError:
    return AppError("Your session has expired. Please sign in again.", 401)


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    settings = get_settings()
    return jwt.PyJWKClient(
        f"{settings.supabase_auth_url}/.well-known/jwks.json",
        cache_keys=True,
        lifespan=3600,
        timeout=int(settings.supabase_timeout_seconds),
    )


def verify_access_token(token: str) -> dict:
    """Return the token's claims, or raise a 401 AppError if it is not valid."""
    settings = get_settings()
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError as exc:
        raise _sign_in_again() from exc

    if algorithm == "HS256":
        return _verify_with_auth_server(token)
    if algorithm not in _ASYMMETRIC_ALGORITHMS:
        raise _sign_in_again()

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError as exc:
        raise ExternalServiceError("Could not reach Supabase to verify your sign-in. Please try again.", 503) from exc
    except jwt.PyJWKClientError as exc:
        raise _sign_in_again() from exc

    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=settings.supabase_auth_url,
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
       logger.error("SUPABASE JWT ERROR: %s", str(exc))
       raise _sign_in_again() from exc

def _verify_with_auth_server(token: str) -> dict:
    key = hashlib.sha256(token.encode()).hexdigest()
    cached = _legacy_cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.supabase_auth_url}/user",
            headers={"apikey": settings.supabase_publishable_key, "Authorization": f"Bearer {token}"},
            timeout=settings.supabase_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise ExternalServiceError("Could not reach Supabase to verify your sign-in. Please try again.", 503) from exc
    if response.status_code != 200:
        raise _sign_in_again()

    user = response.json()
    claims = {
        "sub": user["id"],
        "email": user.get("email"),
        "user_metadata": user.get("user_metadata") or {},
        "app_metadata": user.get("app_metadata") or {},
    }
    _legacy_cache[key] = (time.monotonic() + _LEGACY_CACHE_SECONDS, claims)
    return claims


def user_from_claims(claims: dict) -> CurrentUser:
    metadata = claims.get("user_metadata") or {}
    return CurrentUser(
        id=claims["sub"],
        email=claims.get("email") or metadata.get("email"),
        # Google fills full_name/name and avatar_url/picture.
        full_name=metadata.get("full_name") or metadata.get("name"),
        avatar_url=metadata.get("avatar_url") or metadata.get("picture"),
        provider=(claims.get("app_metadata") or {}).get("provider"),
    )


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    """FastAPI dependency: the signed-in user, or the local user when accounts are off."""
    if not get_settings().auth_enabled:
        return LOCAL_USER
    if credentials is None:
        raise AppError("Please sign in to continue.", 401)
    return user_from_claims(verify_access_token(credentials.credentials))
