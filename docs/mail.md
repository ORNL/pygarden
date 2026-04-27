## Mail

The `pygarden.mail` module provides helpers for sending email from your
applications using a consistent configuration and logging setup.

It is intended for:

- Simple notifications from scripts or services.
- Health or status emails.
- Lightweight alerting without bringing in a full email framework.

---

## Configuration

Although specifics depend on your mail backend, typical environment
variables include:

- `MAIL_SERVER` / `SMTP_SERVER`: hostname of the SMTP server.
- `MAIL_PORT` / `SMTP_PORT`: SMTP port (e.g. `587` for TLS).
- `MAIL_USERNAME`: username for authentication.
- `MAIL_PASSWORD`: password or app-specific token.
- `MAIL_USE_TLS` / `MAIL_USE_SSL`: security mode flags.
- `MAIL_DEFAULT_SENDER`: default `From` address for outgoing emails.

These are read via `pygarden.env.check_environment` so that:

- You can define different values per environment.
- Sensible defaults can be provided for local development.

---

## Sending mail (conceptual)

The mail helper typically exposes a function that:

- Builds an SMTP connection using the configured server, port, and
  security settings.
- Logs successes and failures using `pygarden.logz.create_logger`.
- Optionally supports:
  - Plaintext and HTML bodies.
  - Multiple recipients.
  - Attachments.

Example usage (high-level):

```python
from pygarden.mail import send_mail


send_mail(
    subject="pyGARDEN test",
    recipients=["user@example.com"],
    body="Hello from pyGARDEN!",
)
```

Refer to the docstring and function signature in `pygarden.mail` for the
exact arguments supported by your version.

---

## Best practices

- Store credentials in environment variables, not in source code.
- Use app-specific passwords or secrets management for production.
- Ensure logging is configured to capture errors from the mail subsystem
  without leaking sensitive data.

