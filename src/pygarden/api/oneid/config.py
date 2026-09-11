#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized configuration for the OneID auth plugin.

All settings are read from environment variables at import time via pygarden's
:func:`~pygarden.env.check_environment` helper (aliased as ``ce``).  Override any
setting by exporting the corresponding variable before the module is first imported.

Example minimal ``.env``::

    APP_NAME=MyApp
    ONEID_CLIENT=myapp-client-id
    SESSION_SECRET_KEY=super-secret-change-me
    AUTH_DB_SCHEMA=public
    AUTO_APPROVE_USERS=false
    FIRST_USER_AUTO_ADMIN=true
    SEND_NEW_USER_EMAIL=true
"""

from pygarden.env import check_environment as ce

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------

APP_NAME = ce("APP_NAME", "Application")
"""Human-readable application name used in notification emails."""

PUBLIC_BASE_URL = ce("PUBLIC_BASE_URL", "").strip().rstrip("/")
"""
Canonical public base URL (e.g. ``https://myapp.example.com``).
When empty the URL is inferred from incoming request headers.
"""

ENVIRON = ce("ENVIRON", "prod")
"""
Deployment environment.  Set to ``dev`` to skip JWT signature verification
(useful for local development without a valid OneID token).
"""

# ---------------------------------------------------------------------------
# OneID OAuth 2.0 endpoints
# ---------------------------------------------------------------------------

ONEID_CLIENT = ce("ONEID_CLIENT", "")
"""OAuth client ID registered with your OneID provider."""

ONEID_AUTH_URL = ce("ONEID_AUTH_URL", "https://eams-auth.oneid.energy.gov/as/authorization.oauth2")
"""Authorization endpoint URL."""

ONEID_TOKEN_URL = ce("ONEID_TOKEN_URL", "https://eams-auth.oneid.energy.gov/as/token.oauth2")
"""Token exchange endpoint URL."""

ONEID_JWKS_URL = ce("ONEID_JWKS_URL", "https://eams-auth.oneid.energy.gov/ext/oauth/jwks")
"""JWKS endpoint used to verify JWT signatures."""

# ---------------------------------------------------------------------------
# Session / cookie
# ---------------------------------------------------------------------------

SESSION_SECRET_KEY = ce("SESSION_SECRET_KEY", "changeme-set-SESSION_SECRET_KEY")
"""Secret key used to sign session cookies.  **Always override in production.**"""

SESSION_COOKIE_NAME = ce("SESSION_COOKIE_NAME", "session")
"""Name of the session cookie set on the client."""

SESSION_COOKIE_SECURE = ce("SESSION_COOKIE_SECURE", False)
"""Whether to set the ``Secure`` flag on the session cookie."""

# ---------------------------------------------------------------------------
# URL paths
# ---------------------------------------------------------------------------

OAUTH_REDIRECT_PATH = ce("OAUTH_REDIRECT_PATH", "/login/oauth2/code/oneid")
"""
OAuth callback path registered with your provider.
Must exactly match the redirect URI registered with OneID.
"""

AUTH_REDIRECT_DEFAULT = ce("AUTH_REDIRECT_DEFAULT", "/")
"""Redirect destination after a successful login."""

AUTH_REDIRECT_DISABLED = ce("AUTH_REDIRECT_DISABLED", "/account-status?status=disabled")
"""Redirect when a user's account is disabled."""

AUTH_REDIRECT_UNAPPROVED = ce("AUTH_REDIRECT_UNAPPROVED", "/account-status?status=unapproved")
"""Redirect when a user's account is pending approval."""

AUTH_REDIRECT_CREATED = ce("AUTH_REDIRECT_CREATED", "/account-status?status=created")
"""Redirect when a brand-new user registers and is awaiting approval."""

AUTH_REDIRECT_LOGGED_OUT = ce("AUTH_REDIRECT_LOGGED_OUT", "/account-status?status=logged_out")
"""Redirect after logout."""

AUTH_REDIRECT_UNAUTHORIZED = ce("AUTH_REDIRECT_UNAUTHORIZED", "/account-status?status=unauthorized")
"""Redirect when a non-admin attempts an admin action."""

AUTH_APPROVAL_PATH = ce("AUTH_APPROVAL_PATH", "/approve-user")
"""
Approve-user endpoint path included in new-user notification emails.
Should match ``AUTH_PATH_APPROVE_USER`` (with any router prefix added by the host app).
"""

AUTH_ADMIN_USERS_PATH = ce("AUTH_ADMIN_USERS_PATH", "/admin/users")
"""Admin user-management page path included in notification emails."""

AUTH_PATH_LOGOUT = ce("AUTH_PATH_LOGOUT", "/logout")
"""Router path for the logout endpoint."""

AUTH_PATH_APPROVE_USER = ce("AUTH_PATH_APPROVE_USER", "/approve-user")
"""Router path for the approve-user admin endpoint."""

AUTH_PATH_USER_INFO = ce("AUTH_PATH_USER_INFO", "/user-info")
"""Router path for the user-info endpoint."""

AUTH_PATH_LOGIN_URL = ce("AUTH_PATH_LOGIN_URL", "/login-url")
"""Router path for the login-url helper endpoint."""

# ---------------------------------------------------------------------------
# Database — schema and table names
# ---------------------------------------------------------------------------

AUTH_DB_SCHEMA = ce("AUTH_DB_SCHEMA", ce("DATABASE_SCHEMA", "public"))
"""
Postgres schema that contains the users and sessions tables.
Defaults to ``DATABASE_SCHEMA`` then ``public``.
"""

AUTH_USERS_TABLE = ce("AUTH_USERS_TABLE", "users")
"""Name of the users table."""

AUTH_SESSIONS_TABLE = ce("AUTH_SESSIONS_TABLE", "user_sessions")
"""Name of the user sessions table."""

# ---------------------------------------------------------------------------
# Database — column names (users table)
#
# Override these when integrating with an existing users table whose column
# names differ from the plugin defaults.
#
# Example: if your users table stores the email in a column called
# ``user_email``, set AUTH_COL_EMAIL=user_email.
# ---------------------------------------------------------------------------

COL_USER_ID = ce("AUTH_COL_USER_ID", "user_id")
"""Primary key column of the users table."""

COL_EMAIL = ce("AUTH_COL_EMAIL", "email")
"""Email / login identifier column."""

COL_FIRST_NAME = ce("AUTH_COL_FIRST_NAME", "first_name")
"""Given name column."""

COL_LAST_NAME = ce("AUTH_COL_LAST_NAME", "last_name")
"""Family name column."""

COL_APPROVED = ce("AUTH_COL_APPROVED", "approved")
"""Boolean column indicating whether the account has been approved by an admin."""

COL_ENABLED = ce("AUTH_COL_ENABLED", "enabled")
"""Boolean column indicating whether the account is currently active."""

COL_ADMIN = ce("AUTH_COL_ADMIN", "admin")
"""Boolean column indicating admin privileges."""

COL_US_CITIZEN = ce("AUTH_COL_US_CITIZEN", "us_citizen")
"""DOE citizenship field.  Unused by generic apps; kept for DOE/ORNL compatibility."""

COL_AFFILIATION = ce("AUTH_COL_AFFILIATION", "affiliation")
"""DOE affiliation field.  Unused by generic apps; kept for DOE/ORNL compatibility."""

COL_CREATED_AT = ce("AUTH_COL_CREATED_AT", "created_at")
"""Creation timestamp column."""

COL_UPDATED_AT = ce("AUTH_COL_UPDATED_AT", "updated_at")
"""Last-updated timestamp column."""

# ---------------------------------------------------------------------------
# Database — column names (sessions table)
# ---------------------------------------------------------------------------

COL_SESSION_ID = ce("AUTH_COL_SESSION_ID", "session_id")
"""Session identifier column."""

COL_SESSION_USER_ID = ce("AUTH_COL_SESSION_USER_ID", "user_id")
"""Foreign key column referencing the users table."""

COL_SESSION_DATA = ce("AUTH_COL_SESSION_DATA", "session_data")
"""JSONB column storing the serialized session payload."""

# ---------------------------------------------------------------------------
# Behaviour flags
# ---------------------------------------------------------------------------

SEND_NEW_USER_EMAIL = ce("SEND_NEW_USER_EMAIL", True)
"""
Send an admin notification email when a new user registers.
Set to ``false`` to disable email notifications entirely (e.g. for apps
that do not configure ``pygarden.mail``).
"""

AUTO_APPROVE_USERS = ce("AUTO_APPROVE_USERS", False)
"""
Automatically approve all new user registrations without admin intervention.
Useful for internal tools where any authenticated user should have access.
"""

FIRST_USER_AUTO_ADMIN = ce("FIRST_USER_AUTO_ADMIN", True)
"""
When the very first user registers, automatically approve them and grant admin
privileges.  This bootstraps the admin account so the application is usable
without manual database intervention.  Subsequent users follow the normal
approval flow unless ``AUTO_APPROVE_USERS`` is also ``true``.
"""
