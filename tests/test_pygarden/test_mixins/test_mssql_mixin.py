import os

import pytest

from pygarden.database import Database
from pygarden.mixins.mssql import MSSQLMixin


testcontainers = pytest.importorskip("testcontainers")
from testcontainers.mssql import SqlServerContainer  # noqa: E402


class MSSQLDB(MSSQLMixin, Database):
    pass


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="Skip MSSQL container in CI unless enabled")
def test_mssql_basic_query(has_docker):
    if not has_docker:
        pytest.skip("Docker not available")

    try:
        with SqlServerContainer("mcr.microsoft.com/mssql/server:2022-latest", password="Strong!Passw0rd") as mssql:
            conn_url = mssql.get_connection_url()
            # conn_url like: mssql+pytds://SA:pwd@0.0.0.0:port
            # testcontainers uses pytds driver; our mixin uses pymssql. Parse dsn parts.
            from urllib.parse import urlparse

            u = urlparse(conn_url)
            host = u.hostname or "localhost"
            port = u.port or 1433
            user = u.username or "sa"
            password = u.password or "Strong!Passw0rd"
            dbname = "tempdb"

            db = MSSQLDB(
                connection_info=Database.create_connection_info(
                    db_name=dbname,
                    db_user=user,
                    db_password=password,
                    db_host=f"{host}:{port}",
                    db_engine="mssql+pymssql",
                )
            )
            with db:
                db.query("CREATE TABLE #t(id INT, name VARCHAR(20));")
                db.query("INSERT INTO #t(id,name) VALUES (1,'alice'),(2,'bob');")
                rows = db.query("SELECT * FROM #t ORDER BY id;")
                assert rows == [(1, "alice"), (2, "bob")]
    except Exception as e:
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            pytest.skip(f"Docker container failed to start: {e}")
        raise
