"""Test the DuckDBMixin mixin."""
import pytest

from pygarden.database import Database
from pygarden.mixins.duckdb_mixin import DuckDBMixin


@pytest.fixture
def duckdb_database_fixture():
    """Create a fixture for DuckDBDatabase."""
    class DuckDBDatabase(DuckDBMixin, Database):
        pass

    connection_info = {
        "dbName": ":memory:",
        "dbEngine": "duckdb",
        "dbSchema": "test_schema",
    }
    db = DuckDBDatabase(connection_info=connection_info)
    return db


def test_duckdb_connection(duckdb_database_fixture):
    """Test opening a DuckDB connection."""
    db = duckdb_database_fixture
    with db:
        assert db.connection is not None
        assert db.cursor is not None

def test_duckdb_query(duckdb_database_fixture):
    """Test querying the DuckDB database."""
    db = duckdb_database_fixture
    with db:
        db.query("CREATE TABLE test_table (id INT, name TEXT);")
        db.query("INSERT INTO test_table (id, name) VALUES (1, 'Alice'), (2, 'Bob');")
        rows = db.query("SELECT * FROM test_table ORDER BY id;")
        assert rows == [(1, 'Alice'), (2, 'Bob')]

def test_duckdb_rows_to_dicts(duckdb_database_fixture):
    """Test the _rows_to_dicts method."""
    db = duckdb_database_fixture
    with db:
        db.query("CREATE TABLE test_table (id INT, name TEXT);")
        db.query("INSERT INTO test_table (id, name) VALUES (1, 'Alice'), (2, 'Bob');")
        cursor = db.cursor
        cursor.execute("SELECT * FROM test_table ORDER BY id;")
        rows = cursor.fetchall()
        dict_rows = db._rows_to_dicts(cursor, rows)
        assert dict_rows == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]