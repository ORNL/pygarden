import asyncio

import pytest

from pygarden.database import Database
from pygarden.mixins.asyncpg_mixin import AsyncPostgresMixin


pytest.importorskip("pytest_postgresql")
from pytest_postgresql import factories  # noqa: E402


postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql("postgresql_proc")


class AsyncPGDB(AsyncPostgresMixin, Database):
    pass


@pytest.mark.asyncio
async def test_asyncpg_query_select(postgresql):
    # Extract connection info from the postgresql fixture
    db_name = postgresql.info.dbname
    db_user = postgresql.info.user
    db_password = postgresql.info.password or ""
    db_host = postgresql.info.host
    db_port = postgresql.info.port

    db = AsyncPGDB(
        connection_info=Database.create_connection_info(
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            db_host=db_host,
            db_port=db_port,
            db_engine="postgresql+asyncpg",
        )
    )
    try:
        async with db:
            await db.execute("CREATE TABLE t(id INT PRIMARY KEY, name TEXT);")
            await db.execute("INSERT INTO t(id,name) VALUES (1,'alice'),(2,'bob');")
            rows = await db.query("SELECT * FROM t ORDER BY id;")
            assert [tuple(r) for r in rows] == [(1, "alice"), (2, "bob")]
    finally:
        # ensure closed if async context failed
        if db.is_open():
            await db.close()
