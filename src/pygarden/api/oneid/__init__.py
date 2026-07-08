#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pygarden OneID auth plugin
==========================

A self-contained FastAPI authentication plugin that integrates with the DOE
OneID OAuth 2.0 provider.  It manages user registration, approval, and session
lifecycle backed by a Postgres database.

Quick-start
-----------
Install the ``oneid`` extra::

    uv pip install "pygarden[postgres,oneid]"

Set the required environment variables (see :mod:`pygarden.api.oneid.config`)::

    APP_NAME=MyApp
    ONEID_CLIENT=my-client-id
    SESSION_SECRET_KEY=<random-secret>
    DATABASE_HOST=localhost
    DATABASE_DB=mydb

Mount the router in your FastAPI application::

    from fastapi import FastAPI
    from pygarden.api.oneid import router

    app = FastAPI()
    app.include_router(router)

Protect a route using the :func:`get_user` dependency::

    from fastapi import Depends
    from pygarden.api.oneid import get_user, SessionData

    @app.get("/dashboard")
    async def dashboard(user: SessionData = Depends(get_user)):
        return {"hello": user.first_name}

Handling login redirects
------------------------
When an unauthenticated user hits a protected route, :exc:`RequiresLoginException`
is raised.  Register an exception handler to redirect them to the login page::

    from fastapi.responses import RedirectResponse
    from pygarden.api.oneid import RequiresLoginException, get_login_url

    @app.exception_handler(RequiresLoginException)
    async def require_login_handler(request, _exc):
        response = RedirectResponse(url=get_login_url(request))
        response.set_cookie("redirect_after_login", str(request.url))
        return response
"""

from .auth import (
    RequiresLoginException,
    backend,
    cookie,
    get_login_url,
    get_oauth_redirect_uri,
    get_public_base_url,
    get_session_id,
    get_user,
    send_new_user_email,
    verifier,
)
from .auth_db import AuthDB
from .auth_routes import router
from .session_data import SessionData

__all__ = [
    # Router — mount this in your FastAPI app
    "router",
    # FastAPI dependencies
    "get_user",
    "get_session_id",
    # URL / redirect helpers
    "get_login_url",
    "get_public_base_url",
    "get_oauth_redirect_uri",
    # Session objects (advanced use)
    "cookie",
    "backend",
    "verifier",
    # Data model
    "SessionData",
    # Database class (for extending with custom queries)
    "AuthDB",
    # Exceptions
    "RequiresLoginException",
    # Notification helpers
    "send_new_user_email",
]
