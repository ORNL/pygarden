## SQLAlchemy Integration

PyGARDEN can build **SQLAlchemy engines and sessions** from the same
environment-driven configuration used by the core `Database` and
`PostgresMixin` abstractions. This lets you reuse all of pyGARDEN's
conventions (env vars, logging, retry semantics) while taking advantage
of SQLAlchemy's pooling, transactions, and ORM features.

At a high level:

- **PyGARDEN** remains responsible for configuration, connection info,
  URI generation, and logging.
- **SQLAlchemy** is responsible for connection pooling, session/transaction
  management, and ORM behavior.

Install the extra with:

```bash
pip install "pygarden[sqlalchemy]"
```

This extra installs SQLAlchemy without forcing it on all users.

---

## When to use the psycopg wrapper

The existing `PostgresMixin` (`psycopg`-based) API is still fully
supported and is ideal for:

- **One-off scripts and admin tools** where you just need a simple,
  direct connection.
- **Quick queries** or data inspection using `db.query("SELECT ...")`.
- **Minimal dependencies** when you do not need pooling or an ORM.

Example:

```python
from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin


class PostgresDatabase(Database, PostgresMixin):
    pass


with PostgresDatabase() as db:
    rows = db.query("SELECT NOW()")
```

---

## When to use SQLAlchemy

The SQLAlchemy integration is recommended for:

- **Long‑running services and APIs** where connection pooling and robust
  transaction handling are important.
- **High concurrency workloads** that benefit from SQLAlchemy's pooling
  strategies.
- **ORM usage** with SQLAlchemy's `Session` and declarative models.
- **Migrations and schema management** using tools that expect a
  SQLAlchemy engine (e.g., Alembic).

PyGARDEN provides `SQLAlchemyMixin` and a concrete `SQLAlchemyDatabase`
class that use the same configuration system and environment variables
as the psycopg-based mixins.

---

## Basic engine usage

The simplest way to obtain an Engine is via `SQLAlchemyDatabase`:

```python
from pygarden.sqlalchemy.database import SQLAlchemyDatabase


db = SQLAlchemyDatabase()
engine = db.engine
```

The Engine URL is derived from `Database.create_connection_info()` and:

- URL‑encodes username and password.
- Includes host, port, and database name.
- Preserves the configured engine prefix, defaulting PostgreSQL to
  `postgresql+psycopg`.

PostgreSQL connections also have `search_path` and `application_name`
set on connect, mirroring the behavior of `PostgresMixin.open()`.

---

## Session usage with context manager

For transactional work, use the `session_scope` context manager exposed
by `SQLAlchemyMixin`:

```python
from sqlalchemy import text
from pygarden.sqlalchemy.database import SQLAlchemyDatabase


with SQLAlchemyDatabase() as db:
    with db.session_scope() as session:
        session.execute(text("SELECT 1"))
```

Behavior:

- **Commit on success** when the `with` block exits normally.
- **Rollback on exception**, then re‑raise the error.
- **Always close** the session to return connections to the pool.

You can also obtain a reusable session factory:

```python
from pygarden.sqlalchemy.database import SQLAlchemyDatabase


with SQLAlchemyDatabase() as db:
    Session = db.session_factory()
    with Session() as session:
        ...
```

---

## Choosing between psycopg and SQLAlchemy

- Use **psycopg (`PostgresMixin`)** when you:
  - Need simple, explicit SQL execution in scripts.
  - Prefer direct DB‑API access with minimal layers.
  - Are running short‑lived tools or admin utilities.

- Use **SQLAlchemy (`SQLAlchemyDatabase`)** when you:
  - Are building services, APIs, or applications with many concurrent
    database operations.
  - Want SQLAlchemy's ORM, unit‑of‑work pattern, and migration tooling.
  - Need robust pooling, pre‑ping, and transaction scoping.

Both approaches share the same environment variables and connection
metadata, so you can adopt SQLAlchemy incrementally while keeping
existing psycopg workflows unchanged.

