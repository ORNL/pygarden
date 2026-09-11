#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: integrating the pygarden OneID auth plugin into a FastAPI application.

Copy and adapt this snippet into your application's startup module.

Required environment variables
-------------------------------
The variables below have no safe defaults and **must** be set before the
application starts:

- ``ONEID_CLIENT``       — OAuth client ID registered with your OneID provider
- ``SESSION_SECRET_KEY`` — Random secret used to sign session cookies
- ``DATABASE_HOST``      — Postgres host
- ``DATABASE_DB``        — Postgres database name
- ``DATABASE_USER``      — Postgres username
- ``DATABASE_PW``        — Postgres password

Optional but commonly useful
-----------------------------
- ``APP_NAME``                    — Application name used in notification emails
- ``PUBLIC_BASE_URL``             — Override if running behind a proxy
- ``AUTH_DB_SCHEMA``              — Postgres schema (default: ``public``)
- ``AUTH_USERS_TABLE``            — Users table name (default: ``users``)
- ``AUTH_SESSIONS_TABLE``         — Sessions table name (default: ``user_sessions``)
- ``AUTO_APPROVE_USERS``          — ``true`` to skip manual approval (default: ``false``)
- ``FIRST_USER_AUTO_ADMIN``       — ``true`` to bootstrap the first admin (default: ``true``)
- ``SEND_NEW_USER_EMAIL``         — ``false`` to disable admin notifications (default: ``true``)
- ``OAUTH_REDIRECT_PATH``         — Callback path registered with OneID (default: ``/login/oauth2/code/oneid``)

Column name remapping (if integrating with an existing users table)
-------------------------------------------------------------------
- ``AUTH_COL_EMAIL``       — default: ``email``
- ``AUTH_COL_FIRST_NAME``  — default: ``first_name``
- ``AUTH_COL_LAST_NAME``   — default: ``last_name``
- ``AUTH_COL_APPROVED``    — default: ``approved``
- ``AUTH_COL_ENABLED``     — default: ``enabled``
- ``AUTH_COL_ADMIN``       — default: ``admin``

See :mod:`pygarden.api.oneid.config` for the full list of configurable variables.

Minimal example
---------------
::

    from fastapi import Depends, FastAPI
    from fastapi.responses import RedirectResponse

    from pygarden.api.oneid import (
        RequiresLoginException,
        SessionData,
        get_login_url,
        get_user,
        router as oneid_router,
    )
    from pygarden.api.oneid.auth_db import AuthDB

    app = FastAPI()

    # Mount all OneID routes (login callback, logout, approve-user, user-info, login-url)
    app.include_router(oneid_router)

    # Redirect unauthenticated users to the OneID login page
    @app.exception_handler(RequiresLoginException)
    async def require_login_handler(request, _exc):
        response = RedirectResponse(url=get_login_url(request))
        response.set_cookie("redirect_after_login", str(request.url))
        return response

    # Bootstrap database tables on startup (safe to call repeatedly)
    @app.on_event("startup")
    async def startup():
        async with AuthDB() as adb:
            await adb.create_users_table()
            await adb.create_sessions_table()

    # A protected route
    @app.get("/dashboard")
    async def dashboard(user: SessionData = Depends(get_user)):
        return {"hello": f"{user.first_name} {user.last_name}", "admin": user.admin}
"""
