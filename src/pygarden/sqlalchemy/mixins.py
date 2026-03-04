#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLAlchemy mixin that integrates with the core `Database` abstraction.

This mixin:
- Builds a SQLAlchemy URL from `Database.create_connection_info()`
- Lazily creates and caches an Engine
- Attaches PostgreSQL session parameter hooks (search_path, application_name)
- Exposes session helpers that delegate to `pygarden.sqlalchemy.session`
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import quote_plus

from pygarden.env import check_environment as ce
from pygarden.database import Database

if TYPE_CHECKING:  # pragma: no cover - import-time typing only
    from sqlalchemy.engine import Engine


def _require_sqlalchemy() -> None:
    """
    Ensure SQLAlchemy is available, otherwise raise a helpful error.
    """
    try:
        import sqlalchemy  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only when missing
        msg = (
            "SQLAlchemy is required for SQLAlchemy integration. "
            "Install with `pip install 'pygarden[sqlalchemy]'` or include the "
            "`sqlalchemy` extra."
        )
        raise ImportError(msg) from exc


class SQLAlchemyMixin:
    """
    Mixin that adds SQLAlchemy Engine and Session support to `Database`.

    Expected usage:

    ```python
    from pygarden.database import Database
    from pygarden.sqlalchemy.mixins import SQLAlchemyMixin

    class SQLAlchemyDatabase(Database, SQLAlchemyMixin):
        pass
    ```
    """

    _sqlalchemy_engine: Optional["Engine"] = None

    # ---- URL construction -------------------------------------------------

    def get_sqlalchemy_url(self) -> str:
        """
        Build a SQLAlchemy URL from this instance's `connection_info`.

        - Username and password are URL encoded.
        - Host, port, and database name are included when available.
        - Engine prefix is preserved; for bare PostgreSQL engines we
          default to `postgresql+psycopg`.
        """
        conn: Dict[str, Any] = getattr(self, "connection_info", {}) or {}

        engine = conn.get("dbEngine") or Database.DEFAULT_ENGINE
        # Default to psycopg v3 driver for PostgreSQL if no driver is present
        if engine == "postgresql":
            engine = "postgresql+psycopg"

        # For sqlite, rely on the pre-built URI in connection_info
        if isinstance(engine, str) and engine.startswith("sqlite"):
            uri = conn.get("uri")
            if not uri:
                raise ValueError("SQLite engine requested but no URI was found in connection_info.")
            return uri

        user = conn.get("dbUser", Database.DEFAULT_USER)
        password = conn.get("dbPassword", Database.DEFAULT_PW)
        host = conn.get("dbHost", Database.DEFAULT_HOST)
        port = conn.get("dbPort", Database.DEFAULT_PORT)
        name = conn.get("dbName", Database.DEFAULT_DB)

        user_enc = quote_plus(str(user)) if user is not None else ""
        pw_enc = quote_plus(str(password)) if password is not None else ""

        if not host:
            raise ValueError("Connection info missing 'dbHost'.")
        if not name:
            raise ValueError("Connection info missing 'dbName'.")

        auth = f"{user_enc}:{pw_enc}@" if user_enc or pw_enc else ""
        port_part = f":{port}" if port is not None else ""

        return f"{engine}://{auth}{host}{port_part}/{name}"

    # ---- Engine management ------------------------------------------------

    def create_engine(self, **kwargs: Any) -> "Engine":
        """
        Lazily create and cache a SQLAlchemy Engine.

        Recommended defaults (can be overridden via kwargs):
        - pool_pre_ping = True
        - pool_size = 5
        - max_overflow = 10
        - pool_timeout = 30
        - pool_recycle = 1800
        - future = True
        """
        _require_sqlalchemy()
        from sqlalchemy import create_engine as sa_create_engine

        url = self.get_sqlalchemy_url()

        defaults: Dict[str, Any] = {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "future": True,
        }
        defaults.update(kwargs)

        engine: "Engine" = sa_create_engine(url, **defaults)
        self._attach_postgres_session_listeners(engine)
        self._sqlalchemy_engine = engine
        return engine

    @property
    def engine(self) -> "Engine":
        """Return the cached Engine, creating it on first access."""
        if self._sqlalchemy_engine is None:
            self.create_engine()
        return self._sqlalchemy_engine  # type: ignore[return-value]

    # ---- PostgreSQL session parameters ------------------------------------

    def _attach_postgres_session_listeners(self, engine: "Engine") -> None:
        """
        Attach event listeners that mirror PostgresMixin.open() behavior:

        - SET search_path
        - SET application_name

        These derive from `connection_info` and pyGARDEN's env defaults.
        """
        from sqlalchemy import event

        url_str = str(engine.url)
        if not url_str.startswith("postgresql"):
            return

        conn: Dict[str, Any] = getattr(self, "connection_info", {}) or {}

        schema = conn.get("dbSchema")
        application_name = conn.get("applicationName")

        if not schema:
            schema = ce("DATABASE_SCHEMA", ce("PG_SCHEMA", Database.DEFAULT_SCHEMA))
        search_path = schema

        if not application_name:
            application_name = ce("DATABASE_APPLICATION_NAME", "pygarden")

        @event.listens_for(engine, "connect")  # type: ignore[misc]
        def _on_connect(dbapi_connection, connection_record) -> None:  # pragma: no cover - behavior tested via queries
            cursor = dbapi_connection.cursor()
            try:
                if search_path:
                    cursor.execute(f"SET search_path TO {search_path};")
                if application_name:
                    # Prefer parameterized form (psycopg), fall back to literal
                    try:
                        cursor.execute("SET application_name = %s;", (application_name,))
                    except Exception:
                        cursor.execute(f"SET application_name = '{application_name}';")
            finally:
                cursor.close()

    # ---- Session helpers --------------------------------------------------

    def session_factory(self, **kwargs: Any):
        """
        Return a `sessionmaker` bound to this instance's Engine.
        """
        from .session import session_factory as _session_factory

        return _session_factory(self.engine, **kwargs)

    def session_scope(self, **kwargs: Any):
        """
        Context manager yielding a SQLAlchemy Session bound to this Engine.
        """
        from .session import session_scope as _session_scope

        return _session_scope(self.engine, **kwargs)

    # ---- Database compatibility -------------------------------------------

    def open(self) -> bool:
        """
        Compatibility hook for `Database.__enter__`.

        For SQLAlchemy-driven workflows we do not need a dedicated DB-API
        connection managed by `Database`. We simply ensure the Engine is
        initialized so that downstream code (e.g., `session_scope`) works.
        """
        _ = self.engine
        return True

