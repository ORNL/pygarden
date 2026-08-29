"""Connection and transaction lifecycle for Trellis repositories."""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from pygarden.database import Database
from pygarden.trellis.compiler import CompiledSQL, compile_sql
from pygarden.trellis.config import TrellisConfig
from pygarden.trellis.exceptions import TrellisError
from pygarden.trellis.mapping import map_rows


class TrellisContext:
    """Own and share one async database connection for a unit of work."""

    def __init__(
        self,
        config: TrellisConfig | str | Path = "trellis.toml",
        connection_info: dict[str, Any] | None = None,
        executor: Any | None = None,
    ):
        """Configure a context without opening its database yet."""
        self.config = config if isinstance(config, TrellisConfig) else TrellisConfig.load(config)
        self.connection_info = connection_info
        self.database = executor
        self._owns_database = executor is None
        self._open = False

    def _create_database(self):
        try:
            from pygarden.mixins.asyncpg_mixin import AsyncPostgresMixin
        except ImportError as error:  # pragma: no cover - protected by the extra
            raise TrellisError('Trellis requires the "pygarden[trellis]" extra') from error

        class TrellisDatabase(AsyncPostgresMixin, Database):
            pass

        return TrellisDatabase(connection_info=self.connection_info)

    async def __aenter__(self) -> "TrellisContext":
        """Open the shared database connection."""
        if self.database is None:
            self.database = self._create_database()
        opener = getattr(self.database, "open", None)
        if opener is not None and not self._is_database_open():
            result = opener()
            if inspect.isawaitable(result):
                result = await result
            if result is False:
                raise TrellisError("Unable to open the Trellis database")
        self._open = True
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        """Close a database created by this context."""
        try:
            if self._owns_database and self.database is not None:
                closer = getattr(self.database, "close", None)
                if closer is not None:
                    result = closer()
                    if inspect.isawaitable(result):
                        await result
        finally:
            self._open = False

    def _is_database_open(self) -> bool:
        checker = getattr(self.database, "is_open", None)
        return bool(checker()) if checker is not None else self._open

    def _ensure_open(self):
        if not self._open or self.database is None:
            raise TrellisError("TrellisContext must be entered before repository methods are used")

    def compile(self, sql_file: str | Path, parameters: dict[str, Any]) -> CompiledSQL:
        """Load and compile a SQL file relative to the configured SQL root."""
        path = self.config.resolve_sql(sql_file)
        try:
            template = path.read_text(encoding="utf-8")
        except OSError as error:
            raise TrellisError(f"Unable to read SQL file {path}: {error}") from error
        return compile_sql(template, parameters)

    async def select(self, sql_file: str | Path, parameters: dict[str, Any], result_type: type, cardinality: str):
        """Compile, execute, and map a select statement."""
        self._ensure_open()
        compiled = self.compile(sql_file, parameters)
        rows = await self.database.fetch(compiled.sql, *compiled.arguments)
        return map_rows(rows or [], result_type, cardinality)

    async def command(self, sql_file: str | Path, parameters: dict[str, Any]) -> str | None:
        """Compile and execute a non-query statement."""
        self._ensure_open()
        compiled = self.compile(sql_file, parameters)
        return await self.database.execute(compiled.sql, *compiled.arguments)

    async def select_inline(
        self,
        sql: str,
        result_type: type = dict,
        cardinality: str = "many",
        parameters: dict[str, Any] | None = None,
    ):
        """Compile, execute, and map an inline select statement."""
        self._ensure_open()
        compiled = compile_sql(sql, parameters or {})
        rows = await self.database.fetch(compiled.sql, *compiled.arguments)
        return map_rows(rows or [], result_type, cardinality)

    async def command_inline(self, sql: str, parameters: dict[str, Any] | None = None) -> str | None:
        """Compile and execute an inline non-query statement."""
        self._ensure_open()
        compiled = compile_sql(sql, parameters or {})
        return await self.database.execute(compiled.sql, *compiled.arguments)

    @asynccontextmanager
    async def transaction(self):
        """Create a transaction shared by every repository using this context."""
        self._ensure_open()
        connection = getattr(self.database, "connection", None)
        if connection is None or not hasattr(connection, "transaction"):
            transaction_factory = getattr(self.database, "transaction", None)
            if transaction_factory is None:
                raise TrellisError("The configured executor does not support transactions")
            async with transaction_factory():
                yield self
            return
        async with connection.transaction():
            yield self
