"""Simple session-based auth for deployment gating.

Access is controlled by a single ACCESS_CODE env var. Users enter the code
on a login page, get a session cookie, and can use the dashboard until the
cookie expires. No database, no OAuth, no third-party services.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# Only set secure cookie flag in production (HTTPS)
_IS_PRODUCTION = os.environ.get("RENDER", "") == "true" or os.environ.get("ENV", "") == "production"

# Secret key for signing session tokens (generated once per process)
_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# Access code from env var (required in production)
ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()

# Session duration: 7 days
SESSION_DURATION = 60 * 60 * 24 * 7

COOKIE_NAME = "sez_session"


def _sign_token(timestamp: str) -> str:
    """Create an HMAC-signed session token."""
    sig = hmac.new(_SECRET.encode(), timestamp.encode(), hashlib.sha256).hexdigest()
    return f"{timestamp}|{sig}"


def _verify_token(token: str) -> bool:
    """Verify a session token is valid and not expired."""
    try:
        parts = token.split("|")
        if len(parts) != 2:
            return False
        timestamp, sig = parts
        expected = hmac.new(_SECRET.encode(), timestamp.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        if time.time() - float(timestamp) > SESSION_DURATION:
            return False
        return True
    except (ValueError, TypeError):
        return False


def is_authenticated(request: Request) -> bool:
    """Check if request has a valid session cookie."""
    if not ACCESS_CODE:
        return True  # No access code set = auth disabled
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    return _verify_token(token)


class LoginRequest(BaseModel):
    code: str


@router.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    if not ACCESS_CODE:
        return {"ok": True}
    if not hmac.compare_digest(req.code.strip(), ACCESS_CODE):
        return JSONResponse({"ok": False, "error": "Invalid access code"}, status_code=401)
    token = _sign_token(str(time.time()))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_IS_PRODUCTION,
        samesite="lax",
        max_age=SESSION_DURATION,
    )
    return {"ok": True}


@router.get("/api/auth/check")
async def check_auth(request: Request):
    return {"authenticated": is_authenticated(request)}


@router.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, secure=_IS_PRODUCTION, httponly=True, samesite="lax")
    return {"ok": True}
