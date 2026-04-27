## Configuration and Environment Variables

pyGARDEN is designed to be configured primarily through environment
variables. The core `Database`, mixins, scheduler, and other helpers all
read from the environment using `pygarden.env.check_environment`.

This page summarizes the most important configuration knobs.

---

## Database configuration

Core database settings come from `pygarden.database.Database`:

- **Database identity**:
  - `DATABASE_DB`, `PG_DATABASE`: database name (default: `postgres`).
  - `DATABASE_USER`, `PG_USER`: database user (default: `postgres`).
  - `DATABASE_PW`, `PG_PASSWORD`: database password (default: `postgres`).
  - `DATABASE_HOST`, `PG_HOST`: database host (default: `localhost`).
  - `DATABASE_PORT`, `PG_PORT`: database port (default: `5432`).
- **Schema & engine**:
  - `DATABASE_SCHEMA`, `PG_SCHEMA`: default schema (default: `public`).
  - `DATABASE_ENGINE`: SQLAlchemy engine prefix (default: `postgresql`).
- **Timeout and URI**:
  - `DATABASE_TIMEOUT`, `PG_TIMEOUT`: connect timeout in seconds (default: `60`).
  - `DATABASE_URI`: constructed automatically by `Database.create_connection_info`
    when not explicitly provided.
- **Application name**:
  - `DATABASE_APPLICATION_NAME`: application name attached to DB sessions
    (default: `pygarden`).

Database mixins such as `PostgresMixin`, `MSSQLMixin`, `SQLiteMixin`,
and `AsyncPostgresMixin` typically add their own precedence layer (e.g.
`DATABASE_DB_PG`), but always fall back to the base `Database`
defaults.

---

## Logging configuration

Logging is handled via `pygarden.logz.create_logger`, which is used by
`Database` and other modules.

Key environment variables:

- `DATABASE_LOG_FILE`: file path for database logging (default: `""`, i.e. console only).
- `DATABASE_LOG_MODE`: file mode (`"a"` by default).
- `DATABASE_LOG_ENCODING`: log encoding (`"utf-8"` by default).

When `DATABASE_LOG_FILE` is empty, logs go to the standard pyGARDEN
logger; otherwise, a file-backed logger is created with the specified
mode and encoding.

---

## Scheduler configuration

The background scheduler in `pygarden.scheduler.Scheduler` reads:

- `SCHEDULER_INTERVAL`: default interval configuration for jobs, either:
  - A JSON string, e.g. `{"seconds": 10}`, or
  - A Python-like mapping when used directly in code.
- `SCHEDULER_DB_URL`: SQLAlchemy URL for the APScheduler job store
  (default: `sqlite:////tmp/jobs.sqlite`).

These settings control how often jobs run and where APScheduler stores
its job metadata.

---

## Other configuration surfaces

Several other modules consume environment variables:

- **Mail** (`pygarden.mail`):
  - SMTP server address, port, username, password, TLS/SSL flags, and
    default sender address.
- **Auth and API helpers** (`pygarden.auth`, `pygarden.api.flask`):
  - LDAP/Flask settings for authentication and web APIs.
- **Scrapers** (`pygarden.scrapers` and mixins):
  - Optional settings for proxies, timeouts, and user agents, depending
    on the underlying library.

Each topic-specific page calls out the relevant variables in more
detail, but the overall pattern is:

- Prefer a specific `MODULE_*` variable.
- Fall back to more general `DATABASE_*` or `PG_*` style variables.
- Always provide sensible defaults for local development.
