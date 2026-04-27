## Command-Line Interface (CLI)

pyGARDEN ships with several CLI entry points to make common operations
easy from the command line.

The main console script is exposed in `pyproject.toml` as:

- `pygarden = "pygarden.cli:common_cli"`

Additional command groups live under `pygarden.cli.*`.

---

## CLI entry points

Key modules:

- `pygarden.cli.__init__`:
  - Aggregates CLI commands.
- `pygarden.cli.gen_cli`:
  - Helpers for generating code or boilerplate.
- `pygarden.cli.python_cli`:
  - Python-focused utilities invoked from the command line.
- `pygarden.cli.docker_cli`:
  - Helpers for Docker-related workflows.
- `pygarden.cli.geoparquet_join`:
  - CLI for geospatial/parquet join operations.

These modules are wired into the main `pygarden` command via click (or a
similar CLI framework), so that subcommands are discoverable under:

```bash
pygarden --help
```

---

## Usage

After installing pyGARDEN with the `cli` extra (or `dev`), the
`pygarden` command becomes available:

```bash
pip install "pygarden[cli]"

pygarden --help
pygarden some-subcommand --help
```

Each subcommand module documents its own flags and options via
`--help`. For example, `geoparquet_join` might provide options for
input/output paths, join keys, and projection handling.

---

## Extending the CLI

You can register your own CLI commands by:

- Creating a new module in `pygarden.cli`.
- Exposing click commands (or compatible callables).
- Wiring them into the shared `common_cli` entry point.

Because pyGARDEN already provides logging and configuration utilities,
your commands can easily share:

- Environment-driven settings (see `configuration.md`).
- Centralized logging (see `logging.md`).

