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

# API key header names
ADMIN_API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)
APP_ACCESS_KEY_HEADER = APIKeyHeader(name="X-App-Access-Key", auto_error=False)

# Environment variables
ADMIN_API_KEY_ENV = "ADMIN_API_KEY"
APP_ACCESS_KEY_ENV = "APP_ACCESS_KEY"


def get_admin_api_key() -> Optional[str]:
    """Get the admin API key from environment variable."""
    return os.getenv(ADMIN_API_KEY_ENV)


def get_app_access_key() -> Optional[str]:
    """Get the app access key from environment variable."""
    return os.getenv(APP_ACCESS_KEY_ENV)


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
    api_key: Optional[str] = Security(ADMIN_API_KEY_HEADER),
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


async def require_app_access_key(
    api_key: Optional[str] = Security(APP_ACCESS_KEY_HEADER),
) -> str:
    """
    FastAPI dependency that enforces app-wide access key authentication.

    Usage:
        @router.get("/api/endpoint")
        async def protected_endpoint(
            _: str = Depends(require_app_access_key),
        ):
            ...

    Raises:
        HTTPException 401: If no access key is provided
        HTTPException 403: If the access key is invalid
        HTTPException 503: If the server is misconfigured (no key set)
    """
    expected_key = get_app_access_key()

    # Check if app access key is configured
    if not expected_key:
        LOGGER.error(
            "App access key not configured. Set %s environment variable.",
            APP_ACCESS_KEY_ENV,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="App authentication is not configured. Contact administrator.",
        )

    # Check if access key was provided
    if not api_key:
        LOGGER.warning("App endpoint accessed without access key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access key. Please authenticate.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify the access key
    if not verify_api_key(api_key, expected_key):
        LOGGER.warning("App endpoint accessed with invalid access key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid access key.",
        )

    LOGGER.debug("App access key validated successfully")
    return api_key


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.

    Use this to generate a new API key:
        python -c "from dashboard_api.auth import generate_api_key; print(generate_api_key())"
    """
    return secrets.token_urlsafe(length)


__all__ = [
    "require_admin_api_key",
    "require_app_access_key",
    "generate_api_key",
    "ADMIN_API_KEY_ENV",
    "APP_ACCESS_KEY_ENV",
]
