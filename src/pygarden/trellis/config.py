"""Configuration loading for Trellis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

from pygarden.trellis.exceptions import TrellisConfigError


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_"))


@dataclass(frozen=True)
class TableConfig:
    """A database relation selected for generation."""

    schema: str
    table: str
    model: str
    repository: str
    field_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationConfig:
    """Locations used for generated artifacts."""

    models_output: Path
    repositories_output: Path
    sql_output: Path
    models_module: str | None = None
    imports: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrellisConfig:
    """Validated Trellis configuration."""

    path: Path
    sql_path: Path
    generation: GenerationConfig
    tables: tuple[TableConfig, ...]

    @property
    def base_dir(self) -> Path:
        """Return the directory containing the configuration file."""
        return self.path.parent

    def resolve_sql(self, sql_file: str | Path) -> Path:
        """Resolve a custom SQL path beneath the configured SQL root."""
        candidate = (self.base_dir / self.sql_path / sql_file).resolve()
        root = (self.base_dir / self.sql_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise TrellisConfigError(f"SQL path escapes configured root: {sql_file}")
        return candidate

    @classmethod
    def load(cls, path: str | Path = "trellis.toml") -> "TrellisConfig":
        """Load and validate a standalone Trellis TOML file."""
        config_path = Path(path).expanduser().resolve()
        try:
            with config_path.open("rb") as config_file:
                raw = tomllib.load(config_file)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise TrellisConfigError(f"Unable to load {config_path}: {error}") from error

        root = raw.get("trellis")
        if not isinstance(root, dict):
            raise TrellisConfigError("Configuration must contain a [trellis] table")
        generation = root.get("generate")
        if not isinstance(generation, dict):
            raise TrellisConfigError("Configuration must contain [trellis.generate]")

        required_paths = ("models_output", "repositories_output", "sql_output")
        missing = [name for name in required_paths if not generation.get(name)]
        if missing:
            raise TrellisConfigError(f"Missing generation setting(s): {', '.join(missing)}")

        table_values = root.get("tables", [])
        if not isinstance(table_values, list) or not table_values:
            raise TrellisConfigError("Configure at least one [[trellis.tables]] entry")

        tables: list[TableConfig] = []
        seen: set[tuple[str, str]] = set()
        for item in table_values:
            if not isinstance(item, dict) or not item.get("table"):
                raise TrellisConfigError("Each table entry requires a table name")
            schema = str(item.get("schema", "public"))
            table = str(item["table"])
            identity = (schema, table)
            if identity in seen:
                raise TrellisConfigError(f"Duplicate table configuration: {schema}.{table}")
            seen.add(identity)
            base_name = _pascal_case(table)
            tables.append(
                TableConfig(
                    schema=schema,
                    table=table,
                    model=str(item.get("model", f"Gen{base_name}")),
                    repository=str(item.get("repository", f"Gen{base_name}Repository")),
                    field_overrides=dict(item.get("fields", {})),
                )
            )

        return cls(
            path=config_path,
            sql_path=Path(str(root.get("sql_path", "sql"))),
            generation=GenerationConfig(
                models_output=Path(str(generation["models_output"])),
                repositories_output=Path(str(generation["repositories_output"])),
                sql_output=Path(str(generation["sql_output"])),
                models_module=generation.get("models_module"),
                imports=tuple(str(value) for value in generation.get("imports", ())),
            ),
            tables=tuple(tables),
        )
