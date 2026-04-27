## Database Mixins

Database mixins extend the core `Database` abstraction with concrete
connection logic and convenience methods. They typically implement:

- `open(...)`: to establish a connection using a specific driver.
- `query(...)`: to execute SQL statements.
- Additional helpers tailored to the backend.

This page summarizes the main mixins shipped with pyGARDEN.

## Installing mixins

Use extras to install the dependencies required by non-default mixins:

- `pip install "pygarden[postgres]"`: `PostgresMixin` and `AsyncPostgresMixin`
- `pip install "pygarden[mssql]"`: `MSSQLMixin`
- `pip install "pygarden[duckdb]"`: `DuckDBMixin`
- `pip install "pygarden[db-pandas]"`: `PandasMixin`
- `pip install "pygarden[influx]"`: `InfluxMixin`

`SQLiteMixin` does not require an extra.

If you also need object storage helpers, install the separate `s3` extra:

- `pip install "pygarden[s3]"`

The S3 client is documented on the [S3 utility](../s3.md) page because it is
not a database mixin.

---

## PostgresMixin (`pygarden.mixins.postgres`)

**Backend**: PostgreSQL via `psycopg` (v3).

Responsibilities:

- Opens a psycopg connection with:
  - `dbname`, `user`, `password`, `host`, `port`, `connect_timeout`.
  - `application_name` derived from `connection_info` or environment.
  - `row_factory=dict_row` for dictionary-like results.
- Creates:
  - `cursor`: standard cursor.
  - `dict_cursor`: cursor that returns dict rows.
- Sets `search_path` on connect and commits that change.
- Provides `query(sql, as_dict=False)`:
  - Opens connection on demand if necessary.
  - Executes the SQL and returns `fetchall()` if there is a result set.
  - Logs common psycopg error types.

Key environment variables (in addition to core database vars):

- `DATABASE_DB_PG`, `DATABASE_USER_PG`, `DATABASE_PW_PG`,
  `DATABASE_HOST_PG`, `DATABASE_PORT_PG`:
  - Postgres-specific overrides; fall back to `DATABASE_*` / `PG_*`.
- `DATABASE_SCHEMA_PG`:
  - Overrides default schema for search_path, if set.
- `DATABASE_SEARCH_PATH`:
  - Default search path (default: `"public"`).
- `DATABASE_APPLICATION_NAME`:
  - Application name for the PostgreSQL session (default: `"pygarden"`).

Example:

```python
from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin


class PostgresDatabase(Database, PostgresMixin):
    pass


with PostgresDatabase() as db:
    rows = db.query("SELECT NOW()", as_dict=True)
```

---

## MSSQLMixin (`pygarden.mixins.mssql`)

**Backend**: Microsoft SQL Server via `pymssql`.

Responsibilities:

- Uses `pymssql` to open connections based on `connection_info`.
- Provides a `query` mechanism similar to the Postgres mixin, adapted to
  MSSQL.

Environment and extras:

- Install via the `mssql` extra:
  - `pip install "pygarden[mssql]"`.
- May rely on system libraries (e.g. `freetds` on macOS).

Usage:

```python
from pygarden.database import Database
from pygarden.mixins.mssql import MSSQLMixin


class MSSQLDatabase(Database, MSSQLMixin):
    pass
```

---

## SQLiteMixin (`pygarden.mixins.sqlite`)

**Backend**: SQLite (built-in).

Responsibilities:

- Opens SQLite connections using paths and URIs derived from
  `connection_info` / environment.
- Useful for local development, tests, and lightweight workflows.

Example:

```python
from pygarden.database import Database
from pygarden.mixins.sqlite import SQLiteMixin


class SQLiteDatabase(Database, SQLiteMixin):
    pass
```

---

## AsyncPostgresMixin (`pygarden.mixins.asyncpg_mixin`)

**Backend**: PostgreSQL via `asyncpg` (async I/O).

Responsibilities:

- Provides asynchronous connection and query methods.
- Integrates with `asyncio` to support high-concurrency async workloads.

Install via:

- `pip install "pygarden[postgres]"` (includes `asyncpg`).

Usage pattern (simplified):

```python
import asyncio
from pygarden.database import Database
from pygarden.mixins.asyncpg_mixin import AsyncPostgresMixin


class AsyncPGDatabase(Database, AsyncPostgresMixin):
    pass


async def main():
    db = AsyncPGDatabase()
    async with db:
        rows = await db.query("SELECT 1")


asyncio.run(main())
```

---

## DuckDBMixin (`pygarden.mixins.duckdb_mixin`)

**Backend**: DuckDB.

Responsibilities:

- Provides a connection to DuckDB, typically for analytical workloads or
  local OLAP-style queries.
- Works well with Parquet/Arrow and columnar data processing.

Install via:

- `pip install "pygarden[duckdb]"`.

---

## MultipleMixin (`pygarden.mixins.multiple`)

**Purpose**: Manage **multiple database backends** at once.

Responsibilities:

- Provides a unified interface to multiple underlying databases.
- Allows you to direct queries to the appropriate backend, or iterate
  over configured connections.

Typical usage:

- Centralized configuration for multi-database applications.
- Operations that need to fan out or read from several sources.

---

## PandasMixin (`pygarden.mixins.pandas_mixin`)

**Purpose**: Integrate database access with **pandas**.

Responsibilities:

- Adds helpers to:
  - Run SQL and return `pandas.DataFrame` objects.
  - Write data frames back to the database.

Install via:

- `pip install "pygarden[db-pandas]"` (includes `pandas` and `SQLAlchemy`).

Use when:

- You want ergonomic data analysis operations layered on top of the
  usual `Database` connection handling.

---

## InfluxMixin (`pygarden.mixins.influx`)

**Backend**: InfluxDB.

Responsibilities:

- Provides helpers to connect to and query InfluxDB instances.

Install via:

- `pip install "pygarden[influx]"`.

---

## Choosing a mixin

- Use **PostgresMixin** for direct psycopg access to PostgreSQL.
- Use **MSSQLMixin** for Microsoft SQL Server.
- Use **SQLiteMixin** for local/testing SQLite databases.
- Use **AsyncPostgresMixin** for asynchronous PostgreSQL workloads.
- Use **DuckDBMixin** for analytical workloads with DuckDB.
- Use **MultipleMixin** when managing several databases at once.
- Use **PandasMixin** when you want data frames instead of raw rows.
- Use **InfluxMixin** for time-series data in InfluxDB.

All of these integrate with the same `Database` base class and share the
same configuration philosophy.
