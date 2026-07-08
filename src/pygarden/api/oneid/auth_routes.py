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

import jwt
import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from uuid import UUID, uuid4

from . import config
from .auth import (
    RequiresLoginException,
    backend,
    cookie,
    get_login_url,
    get_oauth_redirect_uri,
    get_user,
    send_new_user_email,
)
from .auth_db import AuthDB
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
async def login_oauth2_callback(code: str, request: Request) -> Response:
    """
    Handle the OneID OAuth 2.0 authorization code callback.

    Exchanges the code for a JWT, extracts user identity, and either creates
    a new session for an existing active user or registers a new user account.

    Auto-approve behaviour:
    - If this is the first user to register, they are automatically approved
      and granted admin privileges (controlled by ``FIRST_USER_AUTO_ADMIN``).
    - If ``AUTO_APPROVE_USERS`` is ``true``, all new registrations are approved
      immediately without requiring admin intervention.

    :param code: Authorization code from OneID.
    :param request: Incoming FastAPI request.
    :returns: Redirect response.
    """
    async with AuthDB() as adb:
        redirect_url = config.AUTH_REDIRECT_DEFAULT
        if request.cookies.get("redirect_after_login"):
            redirect_url = request.cookies.get("redirect_after_login")

        response = RedirectResponse(url=redirect_url)
        if request.cookies.get("redirect_after_login"):
            response.delete_cookie("redirect_after_login")

        # Exchange authorization code for JWT
        jwks_client = PyJWKClient(config.ONEID_JWKS_URL)
        jwt_resp = http_requests.post(
            config.ONEID_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": get_oauth_redirect_uri(request),
                "client_id": config.ONEID_CLIENT,
            },
            timeout=15,
        )
        token = jwt_resp.json().get("access_token")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        verify_signature = config.ENVIRON != "dev"
        jwt_data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_signature": verify_signature},
        )

        email = normalize_email(jwt_data.get("email"))
        if not email:
            raise HTTPException(status_code=401, detail="OneID response did not include an email address.")

        email_status = await adb.getEmailStatus(email)

        # Build the session data from JWT claims.  DOE-specific fields are
        # optional and fall back to their SessionData defaults when absent.
        session_data = SessionData(
            user_id=-1,
            email=email,
            first_name=jwt_data.get("given_name", ""),
            last_name=jwt_data.get("family_name", ""),
            admin=False,
            us_citizen=bool(jwt_data.get("us_citizen", False)),
            affiliation=(
                f"{jwt_data.get('doe_affiliation_level_1', '')}"
                f"/{jwt_data.get('doe_affiliation_level_2', '')}"
            ).strip("/") or "",
        )

        if email_status == "active":
            user = await adb.getUserByEmail(email)
            session_data.user_id = user[config.COL_USER_ID]
            session_data.admin = user.get(config.COL_ADMIN, False)
            session = uuid4()
            await backend.create(session, session_data)
            cookie.attach_to_response(response, session)

        elif email_status == "disabled":
            response = RedirectResponse(url=config.AUTH_REDIRECT_DISABLED)

        elif email_status == "unapproved":
            response = RedirectResponse(url=config.AUTH_REDIRECT_UNAPPROVED)

        else:
            # New user — determine whether to auto-approve
            is_first_user = (await adb.countUsers()) == 0
            should_approve = config.AUTO_APPROVE_USERS or is_first_user
            should_admin = is_first_user and config.FIRST_USER_AUTO_ADMIN

            await adb.createUser(
                email=email,
                first_name=session_data.first_name,
                last_name=session_data.last_name,
                us_citizen=session_data.us_citizen,
                affiliation=session_data.affiliation,
                approved=should_approve,
                admin=should_admin,
            )

            if should_approve:
                # User is immediately active — create a session and log them in
                user = await adb.getUserByEmail(email)
                session_data.user_id = user[config.COL_USER_ID]
                session_data.admin = should_admin
                session = uuid4()
                await backend.create(session, session_data)
                cookie.attach_to_response(response, session)
            else:
                await send_new_user_email(session_data, request)
                response = RedirectResponse(url=config.AUTH_REDIRECT_CREATED)

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
        await adb.approveUser(normalized)
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
def login_url(request: Request):
    """
    Return the OneID login URL for the current request context.

    Useful for front-end clients that need to construct a login button.

    :param request: Incoming FastAPI request.
    :returns: OneID authorization URL string.
    """
    return get_login_url(request)
