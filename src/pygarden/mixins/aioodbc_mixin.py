"""Asynchronous Microsoft SQL Server support through aioodbc."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from pygarden.database import Database
from pygarden.env import check_environment as ce
from pygarden.env import check_multi_environment as cme


class AsyncMSSQLMixin:
    """Provide the async executor contract used by Trellis for SQL Server."""

    DEFAULT_DB = cme("DATABASE_DB_MS", "CommonDB", "DATABASE_DB", "postgres")
    DEFAULT_USER = cme("DATABASE_USER_MS", "sa", "DATABASE_USER", "postgres")
    DEFAULT_PW = cme("DATABASE_PW_MS", "5nowDog5", "DATABASE_PW", "postgres")
    DEFAULT_HOST = cme("DATABASE_HOST_MS", "mssql", "DATABASE_HOST", "localhost")
    DEFAULT_PORT = int(cme("DATABASE_PORT_MS", 1433, "DATABASE_PORT"))
    DEFAULT_SCHEMA = cme("DATABASE_SCHEMA_MS", "dbo", "DATABASE_SCHEMA", "dbo")
    DEFAULT_TIMEOUT = int(cme("DATABASE_TIMEOUT_MS", 60, "DATABASE_TIMEOUT"))
    DEFAULT_ODBC_DRIVER = ce("DATABASE_ODBC_DRIVER_MS", "ODBC Driver 18 for SQL Server")
    DEFAULT_ENCRYPT = ce("DATABASE_ENCRYPT_MS", "yes")
    DEFAULT_TRUST_CERTIFICATE = ce("DATABASE_TRUST_SERVER_CERTIFICATE_MS", "no")

    def __del__(self):
        """Leave asynchronous cleanup to ``close`` or the context manager."""

    @staticmethod
    def _odbc_value(value: Any) -> str:
        """Quote an ODBC connection-string value, including semicolons."""
        return "{" + str(value).replace("}", "}}") + "}"

    @classmethod
    def create_connection_info(cls, **overrides: Any) -> dict[str, Any]:
        """Create connection metadata using MSSQL-specific environment defaults."""
        values = {
            "db_name": cls.DEFAULT_DB,
            "db_user": cls.DEFAULT_USER,
            "db_password": cls.DEFAULT_PW,
            "db_host": cls.DEFAULT_HOST,
            "db_port": cls.DEFAULT_PORT,
            "db_schema": cls.DEFAULT_SCHEMA,
            "db_timeout": cls.DEFAULT_TIMEOUT,
            "db_engine": "mssql+aioodbc",
        }
        database_keys = set(values)
        values.update({key: value for key, value in overrides.items() if key in database_keys})
        info = Database.create_connection_info(**values)
        info.update({key: value for key, value in overrides.items() if key not in database_keys})
        return info

    async def open(self):
        """Open an aioodbc connection using the standard connection-info mapping."""
        try:
            import aioodbc
        except ImportError as error:
            raise ImportError('Install pyGARDEN with the "trellis-mssql" extra') from error

        info = self.connection_info
        driver = info.get("odbcDriver", self.DEFAULT_ODBC_DRIVER)
        host = str(info.get("dbHost", self.DEFAULT_HOST))
        port = int(info.get("dbPort", self.DEFAULT_PORT))
        if "," in host:
            server = host
        elif host.count(":") == 1:
            server = host.replace(":", ",")
        else:
            server = f"{host},{port}"
        value = self._odbc_value
        parts = [
            f"DRIVER={value(driver)}",
            f"SERVER={value(server)}",
            f"DATABASE={value(info.get('dbName', self.DEFAULT_DB))}",
            f"UID={value(info.get('dbUser', self.DEFAULT_USER))}",
            f"PWD={value(info.get('dbPassword', self.DEFAULT_PW))}",
            f"Encrypt={value(info.get('encrypt', self.DEFAULT_ENCRYPT))}",
            f"TrustServerCertificate={value(info.get('trustServerCertificate', self.DEFAULT_TRUST_CERTIFICATE))}",
        ]
        self.connection = await aioodbc.connect(
            dsn=";".join(parts) + ";",
            timeout=int(info.get("dbTimeout", self.DEFAULT_TIMEOUT)),
            autocommit=True,
        )
        return True

    async def close(self):
        """Close the ODBC connection."""
        if self.is_open():
            await self.connection.close()
        self.connection = None

    def is_open(self):
        """Return whether the ODBC connection is available."""
        return getattr(self, "connection", None) is not None and not bool(getattr(self.connection, "closed", False))

    async def _ensure_open(self):
        if not self.is_open():
            await self.open()

    @staticmethod
    def _rows(cursor, rows) -> list[dict[str, Any]]:
        names = [column[0] for column in cursor.description or ()]
        return [dict(zip(names, row)) for row in rows]

    async def fetch(self, query, *args):
        """Execute a query and return rows as mappings."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, tuple(args))
            return self._rows(cursor, await cursor.fetchall())

    async def fetchrow(self, query, *args):
        """Execute a query and return its first row as a mapping."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, tuple(args))
            row = await cursor.fetchone()
            return None if row is None else self._rows(cursor, [row])[0]

    async def execute(self, query, *args):
        """Execute a statement and return a driver-neutral status string."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, tuple(args))
            return None if cursor.rowcount < 0 else f"AFFECTED {cursor.rowcount}"

    async def executemany(self, query, args):
        """Execute one statement for each positional argument sequence."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.executemany(query, args)

    async def query(self, query, *args, as_dict=False):
        """Execute a query using the conventional pyGARDEN mixin interface."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, tuple(args))
            if cursor.description is None:
                return None
            rows = await cursor.fetchall()
            return self._rows(cursor, rows) if as_dict else rows

    async def fetchval(self, query, *args):
        """Execute a query and return the first column of its first row."""
        row = await self.fetchrow(query, *args)
        return None if row is None else next(iter(row.values()))

    @asynccontextmanager
    async def transaction(self):
        """Run statements in a SQL Server transaction."""
        await self._ensure_open()
        async with self.connection.cursor() as cursor:
            await cursor.execute("BEGIN TRANSACTION")
        try:
            yield self
        except BaseException:
            await self.connection.rollback()
            raise
        else:
            await self.connection.commit()

    async def __aenter__(self):
        """Open and return this asynchronous database object."""
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        """Close this asynchronous database object."""
        await self.close()
