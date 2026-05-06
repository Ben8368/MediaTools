"""API key authentication helpers."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from backend.config import API_SECRET_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def api_key_error(supplied_key: str | None, secret_key: str | None = None) -> tuple[int, str] | None:
    """Return an HTTP-style auth error, or None when the supplied key is valid."""
    expected_key = secret_key if secret_key is not None else API_SECRET_KEY
    if not expected_key:
        return None
    if not supplied_key:
        return status.HTTP_401_UNAUTHORIZED, "Missing API key"
    if not secrets.compare_digest(supplied_key, expected_key):
        return status.HTTP_403_FORBIDDEN, "Invalid API key"
    return None


def is_api_key_valid(supplied_key: str | None, secret_key: str | None = None) -> bool:
    return api_key_error(supplied_key, secret_key) is None


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str | None:
    """FastAPI dependency that enforces X-API-Key when API_SECRET_KEY is configured."""
    error = api_key_error(api_key)
    if error:
        status_code, detail = error
        raise HTTPException(status_code=status_code, detail=detail)
    return api_key


def get_optional_api_key(api_key: str | None = Security(api_key_header)) -> str | None:
    """Return a valid optional API key, or None when no valid configured key is present."""
    return api_key if API_SECRET_KEY and is_api_key_valid(api_key) else None
