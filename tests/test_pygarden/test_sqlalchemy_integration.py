import os

import pytest


pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_postgresql")

from pytest_postgresql import factories  # noqa: E402

from pygarden.database import Database  # noqa: E402
from pygarden.sqlalchemy.database import SQLAlchemyDatabase  # noqa: E402
from pygarden.sqlalchemy.mixins import SQLAlchemyMixin  # noqa: E402


postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql("postgresql_proc")


class DummySQLAlchemyDB(Database, SQLAlchemyMixin):
    """Minimal Database+SQLAlchemyMixin implementation for unit tests."""

    def open(self):
        # For these tests we do not need a separate DB-API connection
        # managed by Database; SQLAlchemy manages connections via Engine.
        _ = self.engine
        return True


def _make_connection_info_from_pg(proc) -> dict:
    return Database.create_connection_info(
        db_name=proc.info.dbname,
        db_user=proc.info.user,
        db_password=proc.info.password or "",
        db_host=proc.info.host,
        db_port=proc.info.port,
        db_engine="postgresql",
        db_schema="public",
    )


def test_url_generation_encodes_credentials():
    """Username and password should be URL encoded and driver upgraded."""
    special_user = "user+name@example.com"
    special_pw = "p@ss/word:!"
    info = Database.create_connection_info(
        db_name="testdb",
        db_user=special_user,
        db_password=special_pw,
        db_host="localhost",
        db_port=5432,
        db_engine="postgresql",
    )

    db = DummySQLAlchemyDB(connection_info=info)
    url = db.get_sqlalchemy_url()

    # Driver prefix should be upgraded to psycopg
    assert url.startswith("postgresql+psycopg://")
    # Credentials must be URL encoded
    assert "user%2Bname%40example.com" in url
    assert "p%40ss%2Fword%3A%21" in url


def test_engine_creation_uses_connection_info(postgresql):
    """Engine should be created from Database connection info."""
    info = _make_connection_info_from_pg(postgresql)

    db = DummySQLAlchemyDB(connection_info=info)
    engine = db.engine

    from sqlalchemy.engine import Engine

    assert isinstance(engine, Engine)
    # URL pieces should match the connection info (driver prefix tested above)
    assert engine.url.database == info["dbName"]
    assert engine.url.host == info["dbHost"]
    assert engine.url.port == info["dbPort"]


def test_session_scope_commit_and_rollback(postgresql):
    """session_scope should commit on success and rollback on failure."""
    from sqlalchemy import text

    info = _make_connection_info_from_pg(postgresql)

    db = SQLAlchemyDatabase(connection_info=info)

    # Create table and commit via session_scope
    with db.session_scope() as session:
        session.execute(text("CREATE TABLE t_commit (id INT PRIMARY KEY, name TEXT);"))

    # Successful insert should be committed
    with db.session_scope() as session:
        session.execute(text("INSERT INTO t_commit (id, name) VALUES (1, 'alice');"))

    with db.session_scope() as session:
        rows = session.execute(text("SELECT id, name FROM t_commit ORDER BY id;")).all()
        assert rows == [(1, "alice")]

    # Failed transaction should be rolled back
    with pytest.raises(RuntimeError):
        with db.session_scope() as session:
            session.execute(text("INSERT INTO t_commit (id, name) VALUES (2, 'bob');"))
            # Force an error so that the whole transaction is rolled back
            raise RuntimeError("boom")

    # Verify that the failed transaction did not commit any changes
    with db.session_scope() as session:
        rows = session.execute(text("SELECT COUNT(*) FROM t_commit;")).scalar()
        assert rows == 1


def test_connection_events_set_search_path_and_application_name(postgresql):
    """On-connect hooks should set search_path and application_name."""
    from sqlalchemy import text

    # Use a custom schema and application name to verify behavior
    os.environ["DATABASE_SCHEMA"] = "public"
    os.environ["DATABASE_APPLICATION_NAME"] = "pygarden-sqlalchemy-test"

    info = _make_connection_info_from_pg(postgresql)
    info["dbSchema"] = "public"

    db = SQLAlchemyDatabase(connection_info=info)

    # Use a new session to inspect session settings
    with db.session_scope() as session:
        search_path = session.execute(text("SHOW search_path;")).scalar()
        app_name = session.execute(text("SELECT current_setting('application_name');")).scalar()

        assert "public" in (search_path or "")
        assert app_name == "pygarden-sqlalchemy-test"

