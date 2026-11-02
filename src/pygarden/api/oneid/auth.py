#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core session setup and dependency helpers for the OneID auth plugin.

Exposes FastAPI dependencies (:func:`get_user`, :func:`get_session_id`) and
helpers (:func:`get_login_url`, :func:`get_public_base_url`) for use in route
handlers.  All settings are read from :mod:`pygarden.api.oneid.config`.
"""

from uuid import UUID

from fastapi import HTTPException, Request, Response
from fastapi_sessions.frontends.implementations import CookieParameters, SessionCookie

from pygarden.mail import send_email

from . import config
from .auth_db import AuthDB
from .basic_verifier import BasicVerifier
from .db_backend import DBBackend
from .oidc import begin_login
from .session_data import SessionData


class RequiresLoginError(Exception):
    """Raised when a protected route is accessed without a valid session."""


# Backwards-compatible alias used by existing imports and docs.
RequiresLoginException = RequiresLoginError


# ---------------------------------------------------------------------------
# Session setup — instantiated once at import time using config values
# ---------------------------------------------------------------------------

cookie_params = CookieParameters(secure=config.SESSION_COOKIE_SECURE, samesite="lax")

cookie = SessionCookie(
    cookie_name=config.SESSION_COOKIE_NAME,
    identifier="general_verifier",
    auto_error=True,
    secret_key=config.SESSION_SECRET_KEY,
    cookie_params=cookie_params,
)

backend = DBBackend[UUID, SessionData]()

verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def get_public_base_url(request: Request) -> str:
    """
    Return the canonical public base URL.

    Uses ``PUBLIC_BASE_URL`` from config when set. Development/test may use the
    direct request base URL; forwarded headers are never trusted here.

    :param request: Incoming FastAPI request.
    :returns: Base URL string without a trailing slash.
    :rtype: str
    """
    if config.PUBLIC_BASE_URL:
        return config.PUBLIC_BASE_URL

    if config.ENVIRON.lower() not in {"dev", "development", "test"}:
        raise ValueError("PUBLIC_BASE_URL must be configured outside development")
    return str(request.base_url).rstrip("/")


def get_oauth_redirect_uri(request: Request) -> str:
    """
    Build the full OAuth redirect URI from the base URL and configured path.

    :param request: Incoming FastAPI request.
    :returns: Full redirect URI string.
    :rtype: str
    """
    return f"{get_public_base_url(request)}{config.OAUTH_REDIRECT_PATH}"


def get_login_url(request: Request, response: Response, return_to: str = "/") -> str:
    """
    Build the OneID authorization URL for the login redirect.

    :param request: Incoming FastAPI request.
    :param response: Response that receives the signed OIDC transaction cookie.
    :returns: Full OneID authorization URL.
    :rtype: str
    """
    redirect_uri = get_oauth_redirect_uri(request)
    if config.ENVIRON.lower() not in {"dev", "development", "test"} and not config.SESSION_COOKIE_SECURE:
        raise ValueError("SESSION_COOKIE_SECURE must be enabled outside development")
    if not config.ONEID_ISSUER or not config.ONEID_CLIENT:
        raise ValueError("ONEID_ISSUER and ONEID_CLIENT must be configured")
    return begin_login(
        client_id=config.ONEID_CLIENT,
        client_secret=config.ONEID_CLIENT_SECRET or None,
        authorization_endpoint=config.ONEID_AUTH_URL,
        redirect_uri=redirect_uri,
        session_secret=config.SESSION_SECRET_KEY,
        secure_cookie=config.SESSION_COOKIE_SECURE,
        response=response,
        return_to=return_to,
    )


# ---------------------------------------------------------------------------
# Email notifications (optional — controlled by SEND_NEW_USER_EMAIL)
# ---------------------------------------------------------------------------


async def send_new_user_email(new_user: SessionData, request: Request) -> None:
    """
    Notify admins that a new user has registered and is awaiting approval.

    Does nothing when ``SEND_NEW_USER_EMAIL`` is ``false`` or when there are
    no admin users in the database.

    :param new_user: Session data for the newly registered user.
    :param request: Incoming FastAPI request (used to build approval URLs).
    """
    if not config.SEND_NEW_USER_EMAIL:
        return
    async with AuthDB() as adb:
        admin_emails = await adb.get_admin_emails()
        if not admin_emails:
            return
        base = get_public_base_url(request)
        approval_url = f"{base}{config.AUTH_APPROVAL_PATH}?{config.COL_EMAIL}={new_user.email}"
        send_email(
            f"New {config.APP_NAME} User",
            f"""{config.APP_NAME} Admin,

A new user has registered for {config.APP_NAME}:
- Name:        {new_user.first_name} {new_user.last_name}
- Email:       {new_user.email}
- Affiliation: {new_user.affiliation or "N/A"}

To approve their account, visit:
{approval_url}

- {config.APP_NAME} System
""",
            recipients=",".join(admin_emails),
        )


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------


def get_session_id(redirect: bool = True):
    """
    Return a FastAPI dependency that resolves the current session ID.

    :param redirect: If ``True``, raise :exc:`RequiresLoginException` on
        missing/invalid sessions (triggers a login redirect).  If ``False``,
        raise a 401 HTTP exception instead.
    :returns: Async dependency callable.
    """

    async def _get_session_id(request: Request) -> str:
        try:
            session_id = cookie.__call__(request)
            sd = await backend.read(session_id)
            if sd and sd.user_id > 0:
                async with AuthDB() as adb:
                    if await adb.get_user_status_by_id(sd.user_id) == "active":
                        return str(session_id)
        except Exception:
            pass
        if redirect:
            raise RequiresLoginException()
        raise HTTPException(status_code=401, detail="Not authorized")

    return _get_session_id


async def get_user(request: Request) -> SessionData:
    """
    FastAPI dependency that returns the authenticated :class:`~pygarden.api.oneid.session_data.SessionData`.

    Raises :exc:`RequiresLoginException` for missing sessions and appropriate
    HTTP redirects for disabled or unapproved accounts.

    :param request: Incoming FastAPI request.
    :returns: Validated session data for the active user.
    :rtype: SessionData
    :raises RequiresLoginException: When no valid session exists.
    :raises HTTPException: For disabled (302) or unapproved (302) accounts.
    """
    email_status = "unknown"
    try:
        session_id = cookie.__call__(request)
        sd = await backend.read(session_id)
        if sd and sd.user_id > 0:
            async with AuthDB() as adb:
                email_status = await adb.get_user_status_by_id(sd.user_id)
    except Exception:
        raise RequiresLoginException()

    if email_status == "active":
        return sd
    if email_status == "disabled":
        raise HTTPException(
            status_code=302,
            detail="Not authorized",
            headers={"Location": config.AUTH_REDIRECT_DISABLED},
        )
    if email_status == "unapproved":
        raise HTTPException(
            status_code=302,
            detail="Not authorized",
            headers={"Location": config.AUTH_REDIRECT_UNAPPROVED},
        )
    raise RequiresLoginException()
