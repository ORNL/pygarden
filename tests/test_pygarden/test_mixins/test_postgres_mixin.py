import os

import pytest


pytest.importorskip("pytest_postgresql")
from pytest_postgresql import factories  # noqa: E402


postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql("postgresql_proc")


def test_postgres_query_select(postgresql):
    # Extract connection info from the postgresql fixture
    db_name = postgresql.info.dbname
    db_user = postgresql.info.user
    db_password = postgresql.info.password or ""
    db_host = postgresql.info.host
    db_port = postgresql.info.port

    # Set environment variables for the PostgreSQL connection
    os.environ["POSTGRES_DB"] = postgresql.info.dbname
    os.environ["POSTGRES_USER"] = postgresql.info.user
    os.environ["POSTGRES_PASSWORD"] = postgresql.info.password
    os.environ["POSTGRES_HOST"] = postgresql.info.host
    os.environ["POSTGRES_PORT"] = str(postgresql.info.port)

    from pygarden.database import Database
    from pygarden.mixins.postgres import PostgresMixin

    class PGDB(PostgresMixin, Database):
        pass

    db = PGDB(
        # connection_info=Database.create_connection_info(
        #     db_name=db_name,
        #     db_user=db_user,
        #     db_password=db_password,
        #     db_host=db_host,
        #     db_port=db_port,
        #     db_engine="postgresql",
        # )
    )
    with db:
        db.query("CREATE TABLE t(id INT PRIMARY KEY, name TEXT);")
        db.query("INSERT INTO t(id,name) VALUES (1,'alice'),(2,'bob');")
        rows = db.query("SELECT * FROM t ORDER BY id;", as_dict=True)
        assert [tuple(r) for r in rows] == [(1, "alice"), (2, "bob")]
