"""Authentication utilities for protected endpoints."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

LOGGER = logging.getLogger(__name__)

# API key header name
API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)

# Environment variable for the admin API key
ADMIN_API_KEY_ENV = "ADMIN_API_KEY"


def get_admin_api_key() -> Optional[str]:
    """Get the admin API key from environment variable."""
    return os.getenv(ADMIN_API_KEY_ENV)


def verify_api_key(api_key: str, expected_key: str) -> bool:
    """
    Securely compare API keys using constant-time comparison.

    This prevents timing attacks that could leak information about
    the correct key through response time differences.
    """
    if not api_key or not expected_key:
        return False
    return hmac.compare_digest(api_key, expected_key)


async def require_admin_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """
    FastAPI dependency that enforces admin API key authentication.

    Usage:
        @router.post("/admin/endpoint")
        async def protected_endpoint(
            _: str = Depends(require_admin_api_key),
        ):
            ...

    Raises:
        HTTPException 401: If no API key is provided
        HTTPException 403: If the API key is invalid
        HTTPException 503: If the server is misconfigured (no key set)
    """
    expected_key = get_admin_api_key()

    # Check if admin API key is configured
    if not expected_key:
        LOGGER.error(
            "Admin API key not configured. Set %s environment variable.",
            ADMIN_API_KEY_ENV,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are not configured. Contact administrator.",
        )

    # Check if API key was provided
    if not api_key:
        LOGGER.warning("Admin endpoint accessed without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-Admin-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify the API key
    if not verify_api_key(api_key, expected_key):
        LOGGER.warning("Admin endpoint accessed with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    LOGGER.debug("Admin API key validated successfully")
    return api_key


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.

    Use this to generate a new admin API key:
        python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
    """
    return secrets.token_urlsafe(length)


__all__ = [
    "require_admin_api_key",
    "generate_api_key",
    "ADMIN_API_KEY_ENV",
]
