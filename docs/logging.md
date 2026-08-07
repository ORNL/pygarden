## Logging

pyGARDEN centralizes logging via the `pygarden.logz` module and uses
that logger throughout the package (for databases, scrapers, and other
components).

The goal is to provide:

- **Consistent log formatting** across services and scripts.
- **Simple configuration** via environment variables.
- **Optional file-based logging** for long-running processes.

---

## The `create_logger` helper

The primary entry point is:

- `pygarden.logz.create_logger(path: str | None = None, mode: str = "a", encoding: str = "utf-8")`

Behavior:

- When called **without a path**, it returns a standard application
  logger configured for console output.
- When called **with a path**, it returns a logger that writes to the
  given file with the specified mode and encoding.

The `Database` base class uses `create_logger` like this:

- If `DATABASE_LOG_FILE` (a.k.a. `path`) is empty:
  - A standard logger is used.
- If `DATABASE_LOG_FILE` is non-empty:
  - A dedicated file logger is created with:
    - `DATABASE_LOG_MODE`
    - `DATABASE_LOG_ENCODING`

---

## Environment variables

Key environment variables for database-related logging:

- `DATABASE_LOG_FILE`:
  - File path for logging (default: `""` → no file, console only).
- `DATABASE_LOG_MODE`:
  - File mode, e.g. `"a"` (append) or `"w"` (truncate) (default: `"a"`).
- `DATABASE_LOG_ENCODING`:
  - Encoding for the log file (default: `"utf-8"`).

These are interpreted by `Database.__init__` and passed to
`create_logger`. Other modules may call `create_logger` directly for
their own log streams.

---

## Usage examples

### Simple logger

```python
from pygarden.logz import create_logger

logger = create_logger()
logger.info("Hello from pyGARDEN")
```

### File-based logger for databases

```bash
export DATABASE_LOG_FILE=/var/log/myapp/db.log
export DATABASE_LOG_MODE=a
export DATABASE_LOG_ENCODING=utf-8
```

```python
from pygarden.database import Database


class MyDB(Database):
    def open(self):
        ...


with MyDB() as db:
    db.logger.info("Running a query")
```

The database logger will write to `/var/log/myapp/db.log`, while other
modules continue to use the default logger configuration unless
overridden.

