## File Operations

The `pygarden.file_operations` module contains helpers for interacting
with the filesystem in a safe, reusable way. It is intended to replace
one-off scripts with consistent utilities that:

- Respect pyGARDEN’s logging conventions.
- Are easier to test and reuse.
- Centralize common patterns like reading/writing files, handling
  encodings, and working with temporary paths.

---

## Typical helpers

While exact functions may vary, `file_operations` generally includes
utilities for:

- Reading and writing text or JSON files.
- Ensuring directories exist before writing.
- Listing or globbing files that match certain patterns.
- Handling common error cases (missing files, permission issues) with
  helpful log messages.

These helpers reduce boilerplate in scripts and services that need to
manipulate files alongside other pyGARDEN features (databases, scrapers,
etc.).

---

## Usage patterns

Examples of how you might use these helpers:

```python
from pygarden.file_operations import read_text, write_text


content = read_text("/path/to/input.txt")
write_text("/path/to/output.txt", content.upper())
```

or:

```python
from pygarden.file_operations import ensure_dir, write_json


ensure_dir("/var/app/data")
write_json("/var/app/data/config.json", {"key": "value"})
```

Check the docstrings in `pygarden.file_operations` for the concrete
helpers available in your version and how they handle encodings and
errors.

