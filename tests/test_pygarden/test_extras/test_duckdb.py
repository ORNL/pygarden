"""Tests for the supported DuckDB interface."""

from __future__ import annotations

from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from pygarden.extras.duckdb import DuckDB, DuckDBExtensionError, DuckDBPostgresError  # noqa: E402
from pygarden.mixins.duckdb_mixin import DuckDBMixin  # noqa: E402


def _without_extensions() -> DuckDB:
    """Create a DuckDB instance that performs no extension operations."""
    return DuckDB(spatial=False, postgres=False, parquet=False, httpfs=False)


class _FakeConnection:
    """Record DuckDB calls needed by unit tests."""

    def __init__(self, *, fail_extension: str | None = None, fail_attach: bool = False) -> None:
        """Initialize call recording and optional failure behavior."""
        self.closed = False
        self.description = None
        self.fail_extension = fail_extension
        self.fail_attach = fail_attach
        self.installed: list[str] = []
        self.loaded: list[str] = []
        self.statements: list[str] = []

    def close(self) -> None:
        """Record that the connection was closed."""
        self.closed = True

    def install_extension(self, name: str) -> None:
        """Record an extension installation or simulate its failure."""
        self.installed.append(name)
        if name == self.fail_extension:
            raise RuntimeError("extension unavailable")

    def load_extension(self, name: str) -> None:
        """Record an extension load or simulate its failure."""
        self.loaded.append(name)
        if name == self.fail_extension:
            raise RuntimeError("extension unavailable")

    def execute(self, statement: str, params: object | None = None) -> _FakeConnection:
        """Record SQL or simulate an attachment failure."""
        del params
        self.statements.append(statement)
        if self.fail_attach and statement.startswith("ATTACH"):
            raise RuntimeError("postgresql://admin:secret@example.test/db")
        return self

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return an empty simulated result."""
        return []


def test_import_and_defaults() -> None:
    """The supported class imports with shared defaults and every extension enabled."""
    database = DuckDB()

    assert database.parquet is True
    assert database.spatial is True
    assert database.postgres is True
    assert database.httpfs is True
    assert database.connection is None
    assert database.DEFAULT_DB == DuckDBMixin.DEFAULT_DB
    assert database.DEFAULT_SCHEMA == DuckDBMixin.DEFAULT_SCHEMA
    assert database.DEFAULT_ENGINE == DuckDBMixin.DEFAULT_ENGINE
    assert database.DEFAULT_TIMEOUT == DuckDBMixin.DEFAULT_TIMEOUT
    assert database.DEFAULT_APPLICATION_NAME == DuckDBMixin.DEFAULT_APPLICATION_NAME


def test_in_memory_sql_parameters_and_aliases() -> None:
    """Connections and both SQL method names expose DuckDB results."""
    database = _without_extensions()
    connection = database.open(":memory:")

    assert database.is_open()
    assert connection is database.connection
    assert database.sql("SELECT ? + ?", [2, 3]).fetchall() == [(5,)]
    assert database.query("SELECT $value", {"value": 7}).fetchall() == [(7,)]

    database.close()
    assert not database.is_open()


def test_sql_requires_connection() -> None:
    """SQL execution does not create an implicit connection."""
    with pytest.raises(RuntimeError, match=r"call connect\(\) first"):
        _without_extensions().sql("SELECT 1")


def test_context_manager_connects_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The context manager owns an automatically created connection."""
    monkeypatch.setattr(DuckDB, "DEFAULT_DB", ":memory:")
    database = _without_extensions()

    with database as active:
        assert active is database
        assert database.sql("SELECT 1").fetchall() == [(1,)]

    assert not database.is_open()


def test_file_database_persists_and_reconnects(tmp_path: Path) -> None:
    """A second connection replaces the first and retains file-backed data."""
    path = tmp_path / "example.duckdb"
    database = _without_extensions()
    first = database.connect(path)
    database.sql("CREATE TABLE example AS SELECT 42 AS value")

    second = database.connect(path)

    assert second is not first
    assert database.sql("SELECT value FROM example").fetchall() == [(42,)]
    database.close()


def test_connect_forwards_read_only_and_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connection options are passed to the DuckDB client."""
    captured: dict[str, object] = {}
    connection = _FakeConnection()

    def fake_connect(**kwargs: object) -> _FakeConnection:
        captured.update(kwargs)
        return connection

    monkeypatch.setattr(duckdb, "connect", fake_connect)
    database = _without_extensions()

    assert database.connect("data.duckdb", read_only=True, config={"threads": 1}) is connection
    assert captured == {
        "database": "data.duckdb",
        "read_only": True,
        "config": {"threads": 1},
    }


def test_connect_uses_shared_default_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing path uses the environment-derived legacy default."""
    captured: dict[str, object] = {}
    connection = _FakeConnection()

    def fake_connect(**kwargs: object) -> _FakeConnection:
        captured.update(kwargs)
        return connection

    monkeypatch.setattr(duckdb, "connect", fake_connect)
    monkeypatch.setattr(DuckDB, "DEFAULT_DB", "configured.duckdb")

    _without_extensions().connect()

    assert captured["database"] == "configured.duckdb"


def test_extensions_respect_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only enabled external extensions are installed and loaded."""
    connection = _FakeConnection()
    monkeypatch.setattr(duckdb, "connect", lambda **kwargs: connection)

    DuckDB(spatial=True, postgres=False, parquet=True, httpfs=True).connect()

    assert connection.installed == ["spatial", "httpfs"]
    assert connection.loaded == ["parquet", "spatial", "httpfs"]


def test_extension_failure_closes_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """A required extension failure leaves no partial connection behind."""
    connection = _FakeConnection(fail_extension="spatial")
    monkeypatch.setattr(duckdb, "connect", lambda **kwargs: connection)
    database = DuckDB(spatial=True, postgres=False, parquet=False, httpfs=False)

    with pytest.raises(DuckDBExtensionError, match="spatial"):
        database.connect()

    assert connection.closed
    assert database.connection is None


def test_postgres_uses_temporary_secret() -> None:
    """PostgreSQL credentials are placed in a secret, not ATTACH."""
    connection = _FakeConnection()
    database = DuckDB(spatial=False, postgres=True, parquet=False, httpfs=False)
    database.connection = connection  # type: ignore[assignment]

    database.add_postgres_connection(
        "analytics",
        dsn="postgresql://admin:secret@example.test/db",
        schema="reporting",
        read_only=True,
    )

    create_secret, attach = connection.statements
    assert "CREATE OR REPLACE SECRET" in create_secret
    assert "postgresql://admin:secret@example.test/db" in create_secret
    assert "ATTACH '' AS \"analytics\"" in attach
    assert 'SECRET "pygarden_postgres_analytics"' in attach
    assert "SCHEMA 'reporting'" in attach
    assert "READ_ONLY" in attach
    assert "secret@example.test" not in attach


def test_postgres_validates_inputs() -> None:
    """PostgreSQL attachment rejects disabled and conflicting configurations."""
    disconnected = DuckDB(spatial=False, postgres=True, parquet=False, httpfs=False)
    with pytest.raises(RuntimeError, match="not connected"):
        disconnected.add_postgres_connection("pg", host="localhost")

    disabled = _without_extensions()
    disabled.connection = _FakeConnection()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="postgres=True"):
        disabled.add_postgres_connection("pg", host="localhost")

    enabled = DuckDB(spatial=False, postgres=True, parquet=False, httpfs=False)
    enabled.connection = _FakeConnection()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="either dsn"):
        enabled.add_postgres_connection("pg", "postgresql://localhost/db", host="localhost")


def test_postgres_error_redacts_credentials() -> None:
    """Attachment failures do not expose the credential-bearing DSN."""
    database = DuckDB(spatial=False, postgres=True, parquet=False, httpfs=False)
    database.connection = _FakeConnection(fail_attach=True)  # type: ignore[assignment]

    with pytest.raises(DuckDBPostgresError) as raised:
        database.add_postgres_connection("analytics", "postgresql://admin:secret@example.test/db")

    assert "secret" not in str(raised.value)
    assert raised.value.__cause__ is None


def test_tui_renders_query_and_quits(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The terminal UI executes SQL and exits on its quit command."""
    commands = iter(["SELECT 1 AS value", "\\q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(commands))
    database = _without_extensions()
    database.connect()

    assert database.launch_ui(mode="tui") is None
    output = capsys.readouterr().out
    assert "value" in output
    assert "1" in output


@pytest.mark.parametrize("open_browser", [False, True])
def test_web_ui_is_loopback_only(open_browser: bool) -> None:
    """Web mode configures the native UI without opening a browser by default."""
    connection = _FakeConnection()
    database = _without_extensions()
    database.connection = connection  # type: ignore[assignment]

    url = database.launch_ui(host="localhost", port=9000, mode="web", open_browser=open_browser)

    assert url == "http://localhost:9000"
    assert connection.installed == ["ui"]
    assert connection.loaded == ["ui"]
    expected_call = "CALL start_ui()" if open_browser else "CALL start_ui_server()"
    assert connection.statements == ["SET ui_local_port = 9000", expected_call]


def test_web_ui_rejects_non_loopback_host() -> None:
    """The embedded UI is never represented as a remotely bound server."""
    database = _without_extensions()
    database.connection = _FakeConnection()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="loopback"):
        database.launch_ui(host="0.0.0.0", mode="web")


def test_web_ui_formats_ipv6_url() -> None:
    """IPv6 loopback URLs include the required address brackets."""
    connection = _FakeConnection()
    database = _without_extensions()
    database.connection = connection  # type: ignore[assignment]

    assert database.launch_ui(host="::1", mode="web") == "http://[::1]:8765"
