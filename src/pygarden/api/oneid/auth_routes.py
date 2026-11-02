#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI router providing the OneID OAuth 2.0 callback, logout, and admin endpoints.

Mount this router in your FastAPI application::

    from pygarden.api.oneid import router
    app.include_router(router)

All endpoint paths are configurable via environment variables (see
:mod:`pygarden.api.oneid.config`).  Defaults shown below.

- ``GET {OAUTH_REDIRECT_PATH}``    — OAuth 2.0 callback (default: ``/login/oauth2/code/oneid``)
- ``GET {AUTH_PATH_LOGOUT}``       — Invalidates the current session (default: ``/logout``)
- ``GET {AUTH_PATH_APPROVE_USER}`` — Admin: approve a pending user (default: ``/approve-user``)
- ``GET {AUTH_PATH_USER_INFO}``    — Returns current user's session data (default: ``/user-info``)
- ``GET {AUTH_PATH_LOGIN_URL}``    — Returns the OneID login URL (default: ``/login-url``)
"""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from . import config
from .auth import (
    backend,
    cookie,
    get_login_url,
    get_oauth_redirect_uri,
    get_user,
    send_new_user_email,
)
from .auth_db import AuthDB
from .oidc import callback_return_to, clear_transaction_cookie, validate_callback
from .session_data import SessionData

router = APIRouter()


def normalize_email(email: str | None) -> str:
    """
    Normalise an email address to lowercase with surrounding whitespace removed.

    :param email: Raw email string from the identity provider.
    :returns: Lowercased, stripped email, or an empty string if ``None``.
    :rtype: str
    """
    return (email or "").strip().lower()


@router.get(config.OAUTH_REDIRECT_PATH)
async def login_oauth2_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    """Validate the OIDC response before provisioning or creating a session."""
    if error or not code or not state:
        raise HTTPException(status_code=401, detail="OIDC authorization was not completed")
    if not config.ONEID_ISSUER or not config.ONEID_CLIENT:
        raise HTTPException(status_code=503, detail="OneID is not configured")

    redirect_uri = get_oauth_redirect_uri(request)
    return_to = callback_return_to(request, config.SESSION_SECRET_KEY, state)
    identity = await validate_callback(
        request,
        code=code,
        state=state,
        issuer=config.ONEID_ISSUER,
        client_id=config.ONEID_CLIENT,
        client_secret=config.ONEID_CLIENT_SECRET or None,
        token_endpoint=config.ONEID_TOKEN_URL,
        jwks_uri=config.ONEID_JWKS_URL,
        redirect_uri=redirect_uri,
        session_secret=config.SESSION_SECRET_KEY,
    )
    email = normalize_email(identity.email)
    async with AuthDB() as adb:
        user = await adb.get_user_by_identity(identity.issuer, identity.subject)
        if user is None:
            user = await adb.create_user_for_identity(
                issuer=identity.issuer,
                subject=identity.subject,
                email=email,
                first_name=identity.given_name,
                last_name=identity.family_name,
                approved=config.AUTO_APPROVE_USERS,
            )
        user_id = user[config.COL_USER_ID]
        status = await adb.get_user_status_by_id(user_id)
        if status == "disabled":
            response = RedirectResponse(url=config.AUTH_REDIRECT_DISABLED)
        elif status != "active":
            pending = SessionData(
                user_id=user_id,
                email=email,
                first_name=identity.given_name,
                last_name=identity.family_name,
                admin=False,
                identity_issuer=identity.issuer,
                identity_subject=identity.subject,
            )
            await send_new_user_email(pending, request)
            response = RedirectResponse(url=config.AUTH_REDIRECT_UNAPPROVED)
        else:
            session_data = SessionData(
                user_id=user_id,
                email=email,
                first_name=identity.given_name,
                last_name=identity.family_name,
                admin=bool(user.get(config.COL_ADMIN, False)),
                identity_issuer=identity.issuer,
                identity_subject=identity.subject,
            )
            session = uuid4()
            await backend.create(session, session_data)
            response = RedirectResponse(url=return_to)
            cookie.attach_to_response(response, session)
    clear_transaction_cookie(response, redirect_uri=redirect_uri, secure_cookie=config.SESSION_COOKIE_SECURE)
    return response


@router.get(config.AUTH_PATH_LOGOUT)
async def logout(session_id: UUID = Depends(cookie)):
    """
    Invalidate the current session and clear the session cookie.

    :param session_id: Resolved from the session cookie by FastAPI.
    :returns: Redirect to the logged-out page.
    """
    await backend.delete(session_id)
    response = RedirectResponse(url=config.AUTH_REDIRECT_LOGGED_OUT)
    cookie.delete_from_response(response)
    return response


@router.get(config.AUTH_PATH_APPROVE_USER)
async def approve_user(email: str, user: SessionData = Depends(get_user)):
    """
    Approve a pending user account.  Requires the caller to be an admin.

    :param email: Email address of the user to approve.
    :param user: Current authenticated user (injected by FastAPI).
    :returns: Confirmation string or redirect for non-admins.
    """
    if not user.admin:
        return RedirectResponse(url=config.AUTH_REDIRECT_UNAUTHORIZED, status_code=302)
    async with AuthDB() as adb:
        normalized = normalize_email(email)
        await adb.approve_user(normalized)
        return f"User {normalized} approved"


@router.get(config.AUTH_PATH_USER_INFO)
async def user_info(user: SessionData = Depends(get_user)):
    """
    Return the current authenticated user's session data.

    :param user: Current authenticated user (injected by FastAPI).
    :returns: :class:`~pygarden.api.oneid.session_data.SessionData` as JSON.
    """
    return user


@router.get(config.AUTH_PATH_LOGIN_URL)
def login_url(request: Request, return_to: str = "/"):
    """
    Return the OneID login URL for the current request context.

    Useful for front-end clients that need to construct a login button. The
    response receives a short-lived signed transaction cookie.

    :param request: Incoming FastAPI request.
    :returns: OneID authorization URL string.
    """
    response = JSONResponse(content="")
    url = get_login_url(request, response, return_to=return_to)
    response.body = json.dumps(url).encode()
    response.headers["content-length"] = str(len(response.body))
    return response
