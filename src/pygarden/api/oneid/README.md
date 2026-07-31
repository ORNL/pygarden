# pygarden OneID Auth Plugin

A self-contained FastAPI authentication plugin that integrates with the DOE OneID OAuth 2.0
provider.  It manages user registration, approval, and session lifecycle backed by a Postgres
database.  Everything — including table names, column names, redirect URLs, and behaviour flags
— is configurable via environment variables with sensible defaults.

## Installation

The plugin needs both the `oneid` and `postgres` extras. To install a published
release from PyPI, use either `uv` or `pip`:

```bash
uv pip install "pygarden[postgres,oneid]"
python -m pip install "pygarden[postgres,oneid]"
```

When working from a local checkout of this repository, use either editable
install form:

```bash
uv pip install -e ".[postgres,oneid]"
python -m pip install -e ".[postgres,oneid]"
```

Alternatively, `uv` can synchronize the project environment directly:

```bash
uv sync --extra postgres --extra oneid
```

## Quick-start

1. Set the required environment variables (see [Environment Variables](#environment-variables)):

```bash
export APP_NAME=MyApp
export ONEID_CLIENT=my-client-id
export SESSION_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_HOST=localhost
export DATABASE_DB=mydb
export DATABASE_USER=myuser
export DATABASE_PW=mypassword
```

2. Mount the router and register the exception handler in your FastAPI app:

```python
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
app.include_router(oneid_router)

@app.exception_handler(RequiresLoginException)
async def require_login_handler(request, _exc):
    response = RedirectResponse(url=get_login_url(request))
    response.set_cookie("redirect_after_login", str(request.url))
    return response

@app.on_event("startup")
async def startup():
    async with AuthDB() as adb:
        await adb.create_users_table()
        await adb.create_sessions_table()
```

3. Protect a route:

```python
@app.get("/dashboard")
async def dashboard(user: SessionData = Depends(get_user)):
    return {"hello": f"{user.first_name} {user.last_name}", "admin": user.admin}
```

## Included Endpoints

All endpoint paths are configurable via environment variables.

| Method | Env Var | Default Path | Description |
|--------|---------|--------------|-------------|
| `GET` | `OAUTH_REDIRECT_PATH` | `/login/oauth2/code/oneid` | OAuth 2.0 code callback |
| `GET` | `AUTH_PATH_LOGOUT` | `/logout` | Invalidates session and clears cookie |
| `GET` | `AUTH_PATH_APPROVE_USER` | `/approve-user` | Admin: approve a pending user |
| `GET` | `AUTH_PATH_USER_INFO` | `/user-info` | Returns current user's session data as JSON |
| `GET` | `AUTH_PATH_LOGIN_URL` | `/login-url` | Returns the OneID authorization URL |

## SessionData Fields

| Field | Type | Default | Source |
|-------|------|---------|--------|
| `user_id` | `int` | — | DB primary key |
| `email` | `str` | — | OneID JWT `email` claim |
| `first_name` | `str` | — | OneID JWT `given_name` |
| `last_name` | `str` | — | OneID JWT `family_name` |
| `admin` | `bool` | — | DB `admin` column |
| `us_citizen` | `bool` | `False` | OneID JWT `us_citizen` (DOE apps) |
| `affiliation` | `str` | `""` | OneID JWT DOE affiliation claims |

`us_citizen` and `affiliation` are optional and default to their zero values for non-DOE applications.

## Environment Variables

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Application` | Application name used in email subjects/bodies |
| `PUBLIC_BASE_URL` | _(inferred)_ | Override canonical base URL (e.g. behind a reverse proxy) |
| `ENVIRON` | `prod` | Set to `dev` to skip JWT signature verification |

### OneID OAuth

| Variable | Default | Description |
|----------|---------|-------------|
| `ONEID_CLIENT` | _(required)_ | OAuth client ID registered with your provider |
| `ONEID_AUTH_URL` | EAMS auth URL | Authorization endpoint |
| `ONEID_TOKEN_URL` | EAMS token URL | Token exchange endpoint |
| `ONEID_JWKS_URL` | EAMS JWKS URL | JWT signature verification keys |

### Session / Cookie

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_SECRET_KEY` | _(required)_ | Secret used to sign cookies — **always set in production** |
| `SESSION_COOKIE_NAME` | `session` | Name of the session cookie |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` to add the `Secure` flag to the cookie |

### Routing

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_REDIRECT_PATH` | `/login/oauth2/code/oneid` | OAuth callback path — must match what is registered with OneID |
| `AUTH_PATH_LOGOUT` | `/logout` | Router path for the logout endpoint |
| `AUTH_PATH_APPROVE_USER` | `/approve-user` | Router path for the approve-user endpoint |
| `AUTH_PATH_USER_INFO` | `/user-info` | Router path for the user-info endpoint |
| `AUTH_PATH_LOGIN_URL` | `/login-url` | Router path for the login-url helper endpoint |
| `AUTH_REDIRECT_DEFAULT` | `/` | Redirect after successful login |
| `AUTH_REDIRECT_DISABLED` | `/account-status?status=disabled` | Redirect for disabled accounts |
| `AUTH_REDIRECT_UNAPPROVED` | `/account-status?status=unapproved` | Redirect for pending accounts |
| `AUTH_REDIRECT_CREATED` | `/account-status?status=created` | Redirect when a new user registers and is pending |
| `AUTH_REDIRECT_LOGGED_OUT` | `/account-status?status=logged_out` | Redirect after logout |
| `AUTH_REDIRECT_UNAUTHORIZED` | `/account-status?status=unauthorized` | Redirect for unauthorized admin actions |
| `AUTH_APPROVAL_PATH` | `/approve-user` | Approve-user path linked in admin notification emails |
| `AUTH_ADMIN_USERS_PATH` | `/admin/users` | Admin page path linked in admin notification emails |

### Behaviour

| Variable | Default | Description |
|----------|---------|-------------|
| `SEND_NEW_USER_EMAIL` | `true` | Send admin notification when a new user registers |
| `AUTO_APPROVE_USERS` | `false` | Automatically approve all new registrations |
| `FIRST_USER_AUTO_ADMIN` | `true` | First user to register is auto-approved and granted admin |

### Database — Schema and Table Names

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_DB_SCHEMA` | `DATABASE_SCHEMA` → `public` | Postgres schema containing the auth tables |
| `AUTH_USERS_TABLE` | `users` | Name of the users table |
| `AUTH_SESSIONS_TABLE` | `user_sessions` | Name of the user sessions table |

### Database — Column Names (users table)

Override these when integrating with an existing table that uses different column names.

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_COL_USER_ID` | `user_id` | Primary key |
| `AUTH_COL_EMAIL` | `email` | Email / login identifier |
| `AUTH_COL_FIRST_NAME` | `first_name` | Given name |
| `AUTH_COL_LAST_NAME` | `last_name` | Family name |
| `AUTH_COL_APPROVED` | `approved` | Approval status boolean |
| `AUTH_COL_ENABLED` | `enabled` | Account enabled boolean |
| `AUTH_COL_ADMIN` | `admin` | Admin flag boolean |
| `AUTH_COL_US_CITIZEN` | `us_citizen` | DOE citizenship flag (optional) |
| `AUTH_COL_AFFILIATION` | `affiliation` | DOE affiliation string (optional) |
| `AUTH_COL_CREATED_AT` | `created_at` | Creation timestamp |
| `AUTH_COL_UPDATED_AT` | `updated_at` | Last-updated timestamp |

### Database — Column Names (sessions table)

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_COL_SESSION_ID` | `session_id` | Session identifier |
| `AUTH_COL_SESSION_USER_ID` | `user_id` | Foreign key to users table |
| `AUTH_COL_SESSION_DATA` | `session_data` | JSONB session payload |

## Column-Mapping Example

If your existing users table stores the email address in a column called `user_email`:

```bash
export AUTH_COL_EMAIL=user_email
export AUTH_USERS_TABLE=app_users
export AUTH_DB_SCHEMA=myschema
```

The plugin will use `myschema.app_users.user_email` in all queries without any code changes.

## Auto-Approve & First-User Bootstrapping

By default (`FIRST_USER_AUTO_ADMIN=true`), the first user to register via OneID is automatically
approved and granted admin privileges.  This bootstraps the application without requiring manual
database intervention.

For internal tools where every authenticated user should have access, set:

```bash
export AUTO_APPROVE_USERS=true
```

New users are then logged in immediately after their first OneID authentication.

## Disabling Email Notifications

If your application does not configure `pygarden.mail`, disable notifications so the plugin
does not attempt to send emails:

```bash
export SEND_NEW_USER_EMAIL=false
```

## DOE/OneID App vs Generic OAuth App

**DOE app** — uses `us_citizen` and `affiliation` from JWT claims:

```python
@app.get("/profile")
async def profile(user: SessionData = Depends(get_user)):
    return {
        "name": f"{user.first_name} {user.last_name}",
        "citizen": user.us_citizen,
        "affiliation": user.affiliation,
    }
```

**Generic app** — ignores the DOE fields entirely:

```python
@app.get("/profile")
async def profile(user: SessionData = Depends(get_user)):
    return {"name": f"{user.first_name} {user.last_name}"}
```

`us_citizen` defaults to `False` and `affiliation` defaults to `""` when the JWT does not include them.
