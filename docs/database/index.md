## Database Abstraction

pyGARDEN provides a small but flexible `Database` base class that
standardizes how you:

- Read connection details from **environment variables**.
- Build a reusable `connection_info` dictionary and **URI**.
- Integrate different backends via **mixins**.
- Use Python `with` blocks for **safe transaction handling**.

This page focuses on the core `Database` abstraction. Companion pages
cover specific mixins and SQLAlchemy integration.

---

## The `Database` class

`pygarden.database.Database` is an abstract base class. It does **not**
open connections directly; instead, it expects a mixin (e.g.
`PostgresMixin`, `MSSQLMixin`, `SQLiteMixin`) to implement `open` and
optionally `query`.

Typical usage:

```python
from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin


class PostgresDatabase(Database, PostgresMixin):
    pass


with PostgresDatabase() as db:
    rows = db.query("SELECT NOW()")
```

The constructor reads environment variables, builds `connection_info`,
and prepares a logger.

---

## `connection_info` and URI generation

`Database.create_connection_info(...)` produces a dictionary containing
all connection parameters, including a SQL-style URI string.

Keys include:

- `dbName`, `dbUser`, `dbPassword`
- `dbHost`, `dbPort`
- `dbTimeout`, `dbSchema`
- `dbEngine` (SQLAlchemy/driver engine string)
- `uri` (full connection URI)
- `applicationName`

You can:

- Let pyGARDEN use defaults from environment variables, or
- Override individual pieces:

```python
from pygarden.database import Database

info = Database.create_connection_info(
    db_name="mydb",
    db_user="myuser",
    db_password="secret",
    db_host="db.internal",
    db_port=5432,
    db_engine="postgresql",
)
```

This `connection_info` is consumed by:

- Psycopg-based mixins (e.g. `PostgresMixin`),
- SQLAlchemy integration (see `database/sqlalchemy.md`),
- Other mixins that need consistent DB metadata.

---

## Context manager and transactions

`Database` implements `__enter__` and `__exit__` so you can use it as a
context manager. The pattern is:

```python
with MyDatabase() as db:
    # perform queries
```

Behavior:

- On `__enter__`:
  - Retries opening the connection via `silent_open()`, which calls
    `open()` implemented by a mixin.
  - Logs failures and retries up to `retries` with `retry_interval`.
- On `__exit__`:
  - If no exception occurred:
    - Commits the current transaction (`connection.commit()`).
  - If an exception occurred:
    - Rolls back the transaction (`connection.rollback()`).
  - In all cases:
    - Closes the cursor and connection via `close()`.

This ensures that:

- Code in the `with` block is **atomic** at the connection level.
- Unhandled exceptions trigger a **rollback**, not an accidental commit.

Note: explicit calls to `close()` **do not** perform an extra commit;
they only close resources. Transaction finalization is tied to the
context manager.

---

## Extending `Database` with mixins

To use a specific backend, you mix in an implementation that provides
`open` (and often `query`):

- `pygarden.mixins.postgres.PostgresMixin`
- `pygarden.mixins.mssql.MSSQLMixin`
- `pygarden.mixins.sqlite.SQLiteMixin`
- `pygarden.mixins.asyncpg_mixin.AsyncPostgresMixin`
- `pygarden.mixins.duckdb_mixin.DuckDBMixin`
- `pygarden.mixins.multiple.MultipleMixin`
- `pygarden.mixins.pandas_mixin.PandasMixin`
- `pygarden.mixins.influx.InfluxMixin`

Each mixin knows how to:

- Interpret `connection_info`.
- Open connections using its preferred library.
- Optionally provide convenience methods (`query`, helpers, or adapters).

See `database/mixins.md` for details and examples for each mixin.

---

## SQLAlchemy integration

For users who want full SQLAlchemy workflows (ORM, connection pooling,
sessions), pyGARDEN provides:

- `pygarden.sqlalchemy.mixins.SQLAlchemyMixin`
- `pygarden.sqlalchemy.database.SQLAlchemyDatabase`

These reuse the same `connection_info` and environment variables as the
base `Database` and psycopg mixins, so you can choose between:

- Direct psycopg usage via `PostgresMixin`, or
- Full SQLAlchemy Engine + Session usage via `SQLAlchemyDatabase`.

See `database/sqlalchemy.md` for details.
