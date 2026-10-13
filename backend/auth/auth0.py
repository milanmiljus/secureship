import logging
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch Auth0 JWKS (cached for process lifetime — restart to refresh)."""
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _get_rsa_key(token: str) -> Optional[dict]:
    jwks = _get_jwks()
    header = jwt.get_unverified_header(token)
    for key in jwks.get("keys", []):
        if key["kid"] == header.get("kid"):
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


async def require_admin_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    FastAPI dependency for admin-only routes.

    In dev (AUTH0_DOMAIN not set): always passes, returns a stub admin dict.
    In production: validates the Auth0 JWT, raises 401 on failure.

    SECURITY: This dependency must NEVER be used on chat routes.
    """
    if not settings.AUTH0_DOMAIN:
        logger.warning("AUTH0_DOMAIN not set — admin auth disabled (dev mode)")
        return {"sub": "dev-admin", "email": "dev@secureship.local"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        rsa_key = _get_rsa_key(token)
        if rsa_key is None:
            raise HTTPException(status_code=401, detail="Unable to find matching signing key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
        return payload
    except JWTError as e:
        logger.warning("JWT validation failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
