# DuckDB

DuckDB support is optional. Install it with:

```bash
python -m pip install "pygarden[duckdb]"
```

Use the supported import:

```python
from pygarden.extras.duckdb import DuckDB
```

## Connections and SQL

`DuckDB` uses the database configured by `DATABASE_DB_DUCKDB`, then
`DATABASE_DB`, and finally `:memory:` when no path is supplied. SQL requires an
active connection and supports DuckDB prepared-statement parameters:

For compatibility, `DuckDB.DEFAULT_DB`, `DEFAULT_SCHEMA`, `DEFAULT_ENGINE`,
`DEFAULT_TIMEOUT`, and `DEFAULT_APPLICATION_NAME` reference the corresponding
environment-derived defaults defined by `DuckDBMixin`.

```python
from pygarden.extras.duckdb import DuckDB

with DuckDB() as db:
    rows = db.sql("SELECT ? AS value", [42]).fetchall()
    print(rows)
```

Pass a path for persistent storage, or use `read_only=True` and `config` for
DuckDB connection options:

```python
db = DuckDB(parquet=True, spatial=True, postgres=True, httpfs=True)
db.connect("analytics.duckdb", config={"threads": 4})
db.sql("CREATE TABLE IF NOT EXISTS events (id INTEGER)")
db.close()
```

Parquet, spatial, PostgreSQL, and HTTPFS support are all enabled by default.
DuckDB may need network access to install external extensions on the first
connection. A requested extension that cannot be installed or loaded causes
`connect()` to fail clearly. Pass `False` for extensions that are not needed.

HTTPFS credentials and cloud settings should be supplied through DuckDB's
`config` dictionary, SQL settings/secrets, or the environment.

## Reading Parquet files

DuckDB can query a Parquet file directly without first importing it into a
table. This example enables only Parquet support, which is useful for local or
offline workflows that do not need the other extensions:

```python
from pathlib import Path

from pygarden.extras.duckdb import DuckDB

parquet_path = Path("data/example.parquet")

with DuckDB(
    parquet=True,
    spatial=False,
    postgres=False,
    httpfs=False,
) as db:
    row_count = db.sql(
        "SELECT count(*) FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchone()[0]
    sample = db.sql(
        "SELECT * FROM read_parquet(?) LIMIT 5",
        [str(parquet_path)],
    ).fetchall()

print("Rows:", row_count)
print("Sample:", sample)
```

GeoParquet geometry columns are exposed using DuckDB's geometry types when the
file includes compatible geospatial metadata.

## PostgreSQL

Enable PostgreSQL support when creating the object, connect DuckDB, and attach
the remote database. Credentials are held in a temporary DuckDB secret rather
than included in the `ATTACH` statement:

```python
db = DuckDB(postgres=True)
db.connect()
db.add_postgres_connection(
    "warehouse",
    dsn="postgresql://user:password@db.example.test:5432/analytics",
    schema="reporting",
    read_only=True,
)
rows = db.sql("SELECT * FROM warehouse.reporting.events").fetchall()
```

Individual `host`, `port`, `user`, `password`, and `database` arguments may be
used instead of `dsn`. Attachments are read-write unless `read_only=True`.

## Interactive interfaces

The terminal UI uses Rich to display results and exits on `quit`, `exit`,
`\q`, or end-of-input:

```python
from pygarden.extras.duckdb import DuckDB

with DuckDB() as db:
    db.launch_ui(mode="tui")
```

Web mode starts DuckDB's native loopback server without opening a browser and
returns its URL. Browser launching is explicit, which keeps the default safe
for headless environments. The UI server runs inside the Python process, so
the process and database connection must remain alive while the UI is in use.

Save the following example as a `.py` file and run it normally. Press Enter in
the terminal when you are ready to stop the UI:

```python
from pygarden.extras.duckdb import DuckDB

db = DuckDB()
db.connect(":memory:")

try:
    url = db.launch_ui(
        host="localhost",
        mode="web",
        port=8765,
        open_browser=True,
    )
    print(url)
    input("Press Enter to stop the DuckDB UI...")
finally:
    try:
        db.sql("CALL stop_ui_server()")
    finally:
        db.close()
```

`open_browser=False` starts the same loopback server without opening a browser;
open the returned URL manually. Closing the DuckDB connection or allowing the
Python process to exit stops access to the web UI. If the process exits while
the browser remains open, the browser may report that the internal
`_duckdb_ui` catalog does not exist.

## Deprecated mixin

`pygarden.mixins.duckdb_mixin.DuckDBMixin` remains available for compatibility,
but its `open()` and `query()` methods are deprecated and will be removed in a
future release. New code should use the supported import shown above.
