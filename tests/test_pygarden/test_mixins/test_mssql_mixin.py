import os
import time
import subprocess
from urllib.parse import urlparse

import pytest

from pygarden.database import Database
from pygarden.mixins.mssql import MSSQLMixin

testcontainers = pytest.importorskip("testcontainers")
from testcontainers.core.container import DockerContainer  # noqa: E402

IMAGE = "savannah.ornl.gov/common/mssql:2019-latest"
SA_PASSWORD = os.environ.get("MSSQL_SA_PASSWORD", "Strong!Passw0rd")
os.environ["ACCEPT_EULA"] = "Y"

class MSSQLDB(MSSQLMixin, Database):
    pass

def _need_pull(image: str) -> bool:
    """Check if the image is present locally; if not, we need to pull it."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            text=True,
        )
        return result.stdout.strip() == ""
    except Exception:
        return True

def _can_pull(image: str) -> bool:
    try:
        subprocess.run(
            ["docker", "pull", image],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            timeout=600,
        )
        return True
    except Exception:
        return False


def _wait_for_sqlserver(host: str, port: int, timeout_s: int = 90) -> None:
    """
    Poll until the server accepts a connection. Uses pymssql to attempt a connection.
    :param host: Hostname or IP of the SQL Server.
    :param port: Port number of the SQL Server.
    :param timeout_s: Maximum time to wait in seconds.
    :return: None
    :raises: RuntimeError if the server is not ready within the timeout.
    """
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            import pymssql  # type: ignore

            conn = pymssql.connect(
                server=host,
                user="sa",
                password=SA_PASSWORD,
                database="master",
                port=int(port),
                login_timeout=5,
                timeout=5,
                as_dict=False,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchall()
            conn.close()
            return
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"SQL Server not ready within {timeout_s}s: {last_err!r}")


def test_mssql_basic_query(has_docker):
    if not has_docker:
        pytest.skip("Docker not available")

    if _need_pull(IMAGE) and not _can_pull(IMAGE):
        pytest.skip(f"Cannot pull {IMAGE} (network/registry issue)")

    with DockerContainer(IMAGE) as c:
        (
            c.with_env("ACCEPT_EULA", "Y")
             .with_env("MSSQL_SA_PASSWORD", SA_PASSWORD)
             .with_env("MSSQL_PID", "Developer")
             .with_exposed_ports(1433)
        )
        c.start()

        host = c.get_container_host_ip()
        port = int(c.get_exposed_port(1433))

        # Wait until the server accepts connections
        _wait_for_sqlserver(host, port, timeout_s=120)

        db = MSSQLDB(
            connection_info=Database.create_connection_info(
                db_name="master",
                db_user="sa",
                db_password=SA_PASSWORD,
                db_host=f"{host}:{port}",
                db_engine="mssql+pymssql",
            )
        )

        with db:
            # Use temp table (#t) just like before
            db.query("CREATE TABLE #t(id INT, name VARCHAR(20));")
            db.query("INSERT INTO #t(id,name) VALUES (1,'alice'),(2,'bob');")
            rows = db.query("SELECT id, name FROM #t ORDER BY id;")
            assert rows == [(1, "alice"), (2, "bob")]
