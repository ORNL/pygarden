"""Provide the supported DuckDB interface for pyGARDEN."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from contextlib import suppress
from types import TracebackType
from typing import Literal

import duckdb
from rich.console import Console
from rich.table import Table

from pygarden.mixins.duckdb_mixin import DuckDBMixin

QueryParameters = Mapping[str, object] | Sequence[object]


class DuckDBExtensionError(RuntimeError):
    """Raised when a requested DuckDB extension cannot be loaded."""


class DuckDBPostgresError(RuntimeError):
    """Raised when a PostgreSQL database cannot be attached safely."""


def _quote_identifier(value: str) -> str:
    """Quote a DuckDB identifier."""
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def _quote_literal(value: str) -> str:
    """Quote a DuckDB string literal."""
    return f"'{value.replace(chr(39), chr(39) * 2)}'"


class DuckDB:
    """Manage a DuckDB connection and its optional extensions."""

    DEFAULT_DB = DuckDBMixin.DEFAULT_DB
    DEFAULT_SCHEMA = DuckDBMixin.DEFAULT_SCHEMA
    DEFAULT_ENGINE = DuckDBMixin.DEFAULT_ENGINE
    DEFAULT_TIMEOUT = DuckDBMixin.DEFAULT_TIMEOUT
    DEFAULT_APPLICATION_NAME = DuckDBMixin.DEFAULT_APPLICATION_NAME

    def __init__(
        self,
        *,
        spatial: bool = True,
        postgres: bool = True,
        parquet: bool = True,
        httpfs: bool = True,
    ) -> None:
        """
        Configure extensions to activate when a connection is created.

        Args:
            spatial: Install and load the spatial extension.
            postgres: Install and load the PostgreSQL extension.
            parquet: Load DuckDB's built-in Parquet extension.
            httpfs: Install and load the HTTP/S3 filesystem extension.

        """
        self.spatial = spatial
        self.postgres = postgres
        self.parquet = parquet
        self.httpfs = httpfs
        self.connection: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> DuckDB:
        """Connect to the default database if needed and enter the context."""
        if not self.is_open():
            self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the active connection when leaving the context."""
        self.close()

    def connect(
        self,
        path: str | os.PathLike[str] | None = None,
        read_only: bool = False,
        config: Mapping[str, object] | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """
        Create and store a DuckDB connection.

        An existing connection is closed before the new one is created.

        Args:
            path: Database file path, or ``None`` to use ``DEFAULT_DB``.
            read_only: Whether to open the database without write access.
            config: DuckDB connection configuration values.

        Returns:
            The new live DuckDB connection.

        Raises:
            DuckDBExtensionError: If an enabled extension cannot be installed or loaded.
            duckdb.Error: If DuckDB cannot create the connection.

        """
        self.close()
        database = self.DEFAULT_DB if path is None else os.fspath(path)
        connect_kwargs: dict[str, object] = {"database": database, "read_only": read_only}
        if config is not None:
            connect_kwargs["config"] = dict(config)

        connection = duckdb.connect(**connect_kwargs)
        self.connection = connection
        try:
            self._activate_extensions(connection)
        except Exception as error:
            self.close()
            if isinstance(error, DuckDBExtensionError):
                raise
            raise DuckDBExtensionError("Could not activate the requested DuckDB extensions.") from error
        return connection

    def open(
        self,
        path: str | os.PathLike[str] | None = None,
        read_only: bool = False,
        config: Mapping[str, object] | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """Alias for :meth:`connect`."""
        return self.connect(path=path, read_only=read_only, config=config)

    def close(self) -> None:
        """Close and discard the active connection, if any."""
        if self.connection is None:
            return
        try:
            self.connection.close()
        finally:
            self.connection = None

    def is_open(self) -> bool:
        """Return whether this object currently holds a connection."""
        return self.connection is not None

    def sql(
        self,
        query: str,
        params: QueryParameters | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """
        Execute SQL on the active connection.

        Args:
            query: DuckDB SQL statement to execute.
            params: Optional positional or named prepared-statement parameters.

        Returns:
            DuckDB's connection/result object.

        Raises:
            RuntimeError: If no connection is active.
            duckdb.Error: If DuckDB rejects the statement.

        """
        connection = self._require_connection()
        if params is None:
            return connection.execute(query)
        return connection.execute(query, params)

    def query(
        self,
        query: str,
        params: QueryParameters | None = None,
    ) -> duckdb.DuckDBPyConnection:
        """Alias for :meth:`sql`."""
        return self.sql(query, params)

    def add_postgres_connection(
        self,
        name: str,
        dsn: str | None = None,
        *,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        read_only: bool = False,
    ) -> None:
        """
        Attach PostgreSQL using a temporary DuckDB secret.

        Args:
            name: Catalog name for the attached PostgreSQL database.
            dsn: Full PostgreSQL URI or libpq connection string.
            host: PostgreSQL hostname when a DSN is not supplied.
            port: PostgreSQL port when a DSN is not supplied.
            user: PostgreSQL user when a DSN is not supplied.
            password: PostgreSQL password when a DSN is not supplied.
            database: PostgreSQL database when a DSN is not supplied.
            schema: Optional PostgreSQL schema to expose.
            read_only: Prevent writes through the attached catalog.

        Raises:
            RuntimeError: If no DuckDB connection is active.
            ValueError: If the connection arguments conflict or are incomplete.
            DuckDBPostgresError: If the secret or attachment cannot be created.

        """
        connection = self._require_connection()
        if not self.postgres:
            raise ValueError("PostgreSQL support is disabled; create DuckDB with postgres=True.")
        if not name.strip():
            raise ValueError("PostgreSQL connection name must not be empty.")

        components = {
            "HOST": host,
            "PORT": port,
            "USER": user,
            "PASSWORD": password,
            "DATABASE": database,
        }
        supplied_components = {key: value for key, value in components.items() if value is not None}
        if dsn is not None and supplied_components:
            raise ValueError("Provide either dsn or individual PostgreSQL fields, not both.")
        if dsn is None and not supplied_components:
            raise ValueError("Provide dsn or at least one PostgreSQL connection field.")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("PostgreSQL port must be between 1 and 65535.")

        secret_name = f"pygarden_postgres_{name}"
        secret_sql = self._postgres_secret_sql(secret_name, dsn, supplied_components)
        attach_options = ["TYPE POSTGRES", f"SECRET {_quote_identifier(secret_name)}"]
        if schema is not None:
            attach_options.append(f"SCHEMA {_quote_literal(schema)}")
        if read_only:
            attach_options.append("READ_ONLY")
        attach_sql = f"ATTACH '' AS {_quote_identifier(name)} ({', '.join(attach_options)})"

        try:
            connection.execute(secret_sql)
            connection.execute(attach_sql)
        except Exception:
            with suppress(Exception):
                connection.execute(f"DROP SECRET IF EXISTS {_quote_identifier(secret_name)}")
            raise DuckDBPostgresError(f"Could not attach PostgreSQL database as {name!r}.") from None

    def launch_ui(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        mode: Literal["tui", "web"] = "tui",
        *,
        open_browser: bool = False,
    ) -> str | None:
        """
        Launch a terminal or loopback-only web interface.

        Args:
            host: Loopback hostname used for the returned web URL.
            port: Local port used by the DuckDB web UI.
            mode: ``tui`` for an input loop or ``web`` for DuckDB's native UI.
            open_browser: Open the default browser for web mode when true.

        Returns:
            The web UI URL in web mode, otherwise ``None``.

        Raises:
            RuntimeError: If no connection is active.
            ValueError: If mode, host, or port is invalid.
            DuckDBExtensionError: If DuckDB's UI extension cannot start.

        """
        self._require_connection()
        if mode == "tui":
            self._launch_tui()
            return None
        if mode != "web":
            raise ValueError("mode must be either 'tui' or 'web'.")
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("DuckDB's web UI may only bind to a loopback host.")
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535.")

        connection = self._require_connection()
        try:
            connection.install_extension("ui")
            connection.load_extension("ui")
            connection.execute(f"SET ui_local_port = {port}")
            connection.execute("CALL start_ui()" if open_browser else "CALL start_ui_server()")
        except Exception as error:
            raise DuckDBExtensionError("Could not start the DuckDB web UI.") from error
        url_host = f"[{host}]" if host == "::1" else host
        return f"http://{url_host}:{port}"

    def _activate_extensions(self, connection: duckdb.DuckDBPyConnection) -> None:
        extension_flags = {
            "parquet": self.parquet,
            "spatial": self.spatial,
            "postgres": self.postgres,
            "httpfs": self.httpfs,
        }
        for extension, is_enabled in extension_flags.items():
            if not is_enabled:
                continue
            try:
                if extension != "parquet":
                    connection.install_extension(extension)
                connection.load_extension(extension)
            except Exception as error:
                raise DuckDBExtensionError(f"Could not install or load DuckDB extension {extension!r}.") from error

    def _require_connection(self) -> duckdb.DuckDBPyConnection:
        if self.connection is None:
            raise RuntimeError("DuckDB is not connected; call connect() first.")
        return self.connection

    @staticmethod
    def _postgres_secret_sql(
        secret_name: str,
        dsn: str | None,
        components: Mapping[str, object],
    ) -> str:
        options = ["TYPE POSTGRES"]
        if dsn is not None:
            options.append(f"URI {_quote_literal(dsn)}")
        else:
            for key, value in components.items():
                literal = str(value) if key == "PORT" else _quote_literal(str(value))
                options.append(f"{key} {literal}")
        return f"CREATE OR REPLACE SECRET {_quote_identifier(secret_name)} ({', '.join(options)})"

    def _launch_tui(self) -> None:
        console = Console()
        console.print("DuckDB SQL console. Enter quit, exit, or \\q to stop.")
        while True:
            try:
                query = input("duckdb> ").strip()
            except EOFError:
                return
            if query.lower() in {"quit", "exit", "\\q"}:
                return
            if not query:
                continue
            try:
                result = self.sql(query)
                self._render_result(console, result)
            except duckdb.Error as error:
                console.print(f"[red]DuckDB error:[/red] {error}")

    @staticmethod
    def _render_result(console: Console, result: duckdb.DuckDBPyConnection) -> None:
        if result.description is None:
            console.print("OK")
            return
        table = Table()
        for column in result.description:
            table.add_column(str(column[0]))
        for row in result.fetchall():
            table.add_row(*(str(value) if value is not None else "NULL" for value in row))
        console.print(table)


__all__ = ["DuckDB", "DuckDBExtensionError", "DuckDBPostgresError"]
