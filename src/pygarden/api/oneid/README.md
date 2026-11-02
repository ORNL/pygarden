# pyGARDEN OneID Authentication

The `oneid` extra provides a FastAPI authorization-code integration using Authlib,
PyJWT, and the configured OneID endpoints. The callback validates a signed ID token
before the plugin looks up an account or creates an application session. ESDX uses
the lower-level validated-identity interface and retains its own identity, approval,
and RBAC tables.

## Install and configure

```sh
uv sync --extra oneid --extra postgres
```

Set these environment variables before importing `pygarden.api.oneid.config`:

| Variable | Purpose |
|---|---|
| `ONEID_CLIENT` | Registered OIDC client identifier and expected ID-token audience |
| `ONEID_CLIENT_SECRET` | Client secret when the registered application requires it |
| `ONEID_ISSUER` | Exact issuer value expected in ID tokens |
| `ONEID_AUTH_URL` | Authorization endpoint |
| `ONEID_TOKEN_URL` | Token endpoint |
| `ONEID_JWKS_URL` | Trusted signing-key endpoint |
| `OAUTH_REDIRECT_PATH` | Callback path registered with the provider |
| `PUBLIC_BASE_URL` | Canonical externally visible HTTPS origin in production |
| `SESSION_SECRET_KEY` | Random secret of at least 32 characters |
| `SESSION_COOKIE_SECURE` | Set to `true` for production HTTPS |
| `ENVIRON` | Deployment environment; does not disable token validation |

The endpoints and issuer must use HTTPS. HTTP is accepted only for loopback
addresses such as `127.0.0.1` or `localhost`, to support local provider tests.
Forwarded host/protocol headers are not trusted; production deployments must set
`PUBLIC_BASE_URL`. Register the exact callback URI, including scheme, host, and
`OAUTH_REDIRECT_PATH`, with OneID.

## Application-managed identity boundary

Applications that own their user model should use the public boundary:

```python
from pygarden.api.oneid import ValidatedIdentity, begin_login, validate_callback
```

`begin_login` creates state, nonce, and an S256 PKCE verifier, stores the transaction
in a short-lived authenticated-encrypted HttpOnly cookie, and returns the authorization URL.
`validate_callback` checks the signed transaction, exchanges the one-use code with
the PKCE verifier, validates the ID-token signature and approved algorithm, issuer,
audience, temporal claims, subject, nonce, and authorized party, and returns a
`ValidatedIdentity`. Applications should provision users only after this function
returns successfully. The token endpoint response's access token is not treated as
an identity token.

The callback handler may be mounted with `router` for pyGARDEN's standalone user and
session tables. The plugin creates `user_identities` mapping rows by unique `(issuer,
subject)` pairs. Its idempotent schema upgrade removes a legacy single-column unique
constraint on email when present, but it does not link existing accounts. Existing
rows remain unlinked until an operator performs a separate verified identity-linking
procedure. Email changes do not change the mapped identity, and equal email values
do not merge accounts.

`get_login_url(request, response, return_to=...)` requires the response so it can set
the encrypted state transaction cookie. `return_to` must be a local path; external redirect
targets are rejected. In production, configure `PUBLIC_BASE_URL` and secure cookies.

## Standalone router and database

```python
from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse

from pygarden.api.oneid import (
    RequiresLoginException,
    SessionData,
    get_login_url,
    get_user,
    router,
)
from pygarden.api.oneid.auth_db import AuthDB

app = FastAPI()
app.include_router(router)

@app.exception_handler(RequiresLoginException)
async def require_login_handler(request, _exc):
    response = RedirectResponse(url="/")
    response.headers["location"] = get_login_url(request, response, return_to="/dashboard")
    return response

@app.on_event("startup")
async def startup():
    async with AuthDB() as database:
        await database.create_users_table()
        await database.create_sessions_table()

@app.get("/dashboard")
async def dashboard(user: SessionData = Depends(get_user)):
    return {"hello": user.first_name}
```

`create_users_table()` also runs the identity-table schema upgrade. In production,
prefer applying database changes through a reviewed migration before deploying the
new package. The upgrade requires PostgreSQL DDL permissions.

The compatibility variable `FIRST_USER_AUTO_ADMIN` is deprecated and defaults to
false; the OneID login callback never grants administrator privileges. `AUTO_APPROVE_USERS`
can still approve new plugin accounts when explicitly enabled, but does not grant admin.
ESDX does not use the plugin's standalone user/session database or its authorization
routes; it uses only the validated identity API and applies its own PostgreSQL RBAC.

## Security behavior and test coverage

Every environment enforces RS256 signature verification with a matching trusted JWKS
signing key, exact issuer, client-ID audience, expiration/issued-at claims, nonempty subject,
state, nonce, and S256 PKCE. Callback replay is rejected by one-use authorization
codes. The login transaction cookie is authenticated-encrypted, HttpOnly, SameSite=Lax,
and short-lived.
Token and key-fetch failures fail closed. Tokens and client secrets are not logged.

Regression tests use a local authorization-code provider and cover invalid issuer,
audience, signature, expiration, missing/mismatched nonce, missing subject, state,
replay, email changes, duplicate email, and unsafe redirect targets. Those tests do
not substitute for an institutional OneID registration or deployment test.
