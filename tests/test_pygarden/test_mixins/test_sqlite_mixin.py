import pytest

from pygarden.database import Database
from pygarden.mixins.sqlite import SQLiteMixin


class SQLiteDB(SQLiteMixin, Database):
    pass


def test_sqlite_in_memory_query():
    db = SQLiteDB(connection_info=Database.create_connection_info(db_engine="sqlite", db_name=":memory:"))
    with db:
        db.query("CREATE TABLE t(a INTEGER, b TEXT);")
        db.query("INSERT INTO t(a,b) VALUES (1,'x'),(2,'y');")
        rows = db.query("SELECT * FROM t ORDER BY a;")
        assert rows == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
