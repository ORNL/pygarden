## Auth

The `pygarden.auth` module provides helpers for authentication-related
workflows, particularly in combination with LDAP and Flask-based APIs.

It is designed to integrate with:

- Environment-driven configuration for directories and credentials.
- pyGARDEN logging for traceability.
- Web frameworks such as Flask or related tools.

---

## Typical responsibilities

Depending on your deployment, `pygarden.auth` may help you:

- Connect to an LDAP/Active Directory server.
- Validate user credentials.
- Fetch user attributes or group memberships.
- Integrate authentication checks into web routes.

These helpers allow you to centralize:

- Connection configuration (host, port, TLS/SSL).
- Bind credentials (service accounts).
- Timeouts and retry behavior.

---

## Related extras

The `auth` extra in `pyproject.toml` installs:

- `ldap3`
- `flask`

Install via:

```bash
pip install "pygarden[auth]"
```

This gives you the dependencies needed for:

- LDAP integration.
- Flask-based APIs that consume pyGARDEN auth utilities.

---

## Integration with Flask APIs

The `pygarden.api.flask` package contains helpers and routes that can
work alongside `pygarden.auth` to:

- Protect endpoints with authentication checks.
- Use LDAP or other backends as the source of truth.
- Surface detailed logging for authentication success/failure events.

Refer to:

- `pygarden.api.flask.__init__`
- `pygarden.api.flask.routes`

for the specific routes and patterns exposed in your version.

