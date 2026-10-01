"""Tests for the Trellis data mapper."""

# ruff: noqa: D100, D101, D102, D103, D105, D107

from pathlib import Path

import pytest

from pygarden.trellis import (
    TrellisCardinalityError,
    TrellisConfig,
    TrellisContext,
    TrellisError,
    TrellisRepository,
    TrellisTemplateError,
    command_many,
    compile_sql,
    inline_command,
    inline_select,
    map,
    map_rows,
    model,
    select,
)
from pygarden.trellis.generator import Column, Relation, TrellisGenerator


def write_config(tmp_path: Path, driver: str = "postgres", name: str = "trellis.toml") -> Path:
    config = tmp_path / name
    config.write_text(
        f"""
[trellis]
driver = "{driver}"
sql_path = "sql"

[trellis.generate]
models_output = "src/example/models/generated.py"
repositories_output = "src/example/repositories/generated.py"
sql_output = "sql/generated"

[[trellis.tables]]
schema = "public"
table = "users"
model = "GenUser"
repository = "GenUserRepository"
""",
        encoding="utf-8",
    )
    return config


def test_config_loads_and_resolves_sql(tmp_path):
    config = TrellisConfig.load(write_config(tmp_path))
    assert config.driver == "postgres"
    assert config.tables[0].model == "GenUser"
    assert config.resolve_sql("users/select.sql") == tmp_path / "sql/users/select.sql"


def test_mssql_config_defaults_to_dbo_schema(tmp_path):
    config_path = tmp_path / "mssql.toml"
    config_path.write_text(
        """
[trellis]
driver = "mssql"

[trellis.generate]
models_output = "models.py"
repositories_output = "repositories.py"
sql_output = "sql/generated"

[[trellis.tables]]
table = "users"
""",
        encoding="utf-8",
    )
    config = TrellisConfig.load(config_path)
    assert config.driver == "mssql"
    assert config.tables[0].schema == "dbo"


def test_mssql_context_builds_async_database_with_mssql_connection_info(tmp_path):
    from pygarden.mixins.aioodbc_mixin import AsyncMSSQLMixin

    context = TrellisContext(write_config(tmp_path, "mssql"))
    database = context._create_database()
    assert isinstance(database, AsyncMSSQLMixin)
    assert database.connection_info["dbEngine"] == "mssql+aioodbc"


class FakeODBCCursor:
    description = (("user_id", int, None, None, None, None, False),)
    rowcount = 1

    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, sql, parameters=()):
        self.calls.append((sql, parameters))

    async def executemany(self, sql, parameters):
        self.calls.append((sql, parameters))

    async def fetchall(self):
        return [(7,)]

    async def fetchone(self):
        return (7,)


class FakeODBCConnection:
    closed = False

    def __init__(self):
        self.cursors = []
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        cursor = FakeODBCCursor()
        self.cursors.append(cursor)
        return cursor

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_async_mssql_mixin_implements_trellis_executor_contract(tmp_path):
    context = TrellisContext(write_config(tmp_path, "mssql"))
    database = context._create_database()
    connection = FakeODBCConnection()
    database.connection = connection

    assert await database.fetch("SELECT user_id FROM users WHERE user_id=?", 7) == [{"user_id": 7}]
    assert await database.fetchrow("SELECT user_id FROM users WHERE user_id=?", 7) == {"user_id": 7}
    assert await database.fetchval("SELECT user_id FROM users WHERE user_id=?", 7) == 7
    assert await database.execute("UPDATE users SET user_id=?", 7) == "AFFECTED 1"
    await database.executemany("UPDATE users SET user_id=?", [(7,), (8,)])
    async with database.transaction():
        pass
    assert connection.cursors[0].calls == [("SELECT user_id FROM users WHERE user_id=?", (7,))]
    assert connection.cursors[-1].calls == [("BEGIN TRANSACTION", ())]
    assert connection.committed


def test_compiler_handles_conditions_choose_and_named_binds():
    template = """SELECT * FROM users
-- trellis: if active
WHERE active = :active
-- trellis: elif user_id is not None
WHERE user_id = :user_id
-- trellis: else
WHERE false
-- trellis: endif
-- trellis: choose order
-- trellis: when "name"
ORDER BY name
-- trellis: otherwise
ORDER BY user_id
-- trellis: endchoose
"""
    compiled = compile_sql(template, {"active": False, "user_id": 4, "order": "name"})
    assert "WHERE user_id = $1" in compiled.sql
    assert "ORDER BY name" in compiled.sql
    assert compiled.arguments == (4,)


def test_compiler_uses_mssql_qmark_binds():
    compiled = compile_sql(
        "SELECT * FROM [users] WHERE [user_id]=:user_id AND [name]=:name",
        {"user_id": 4, "name": "Ada"},
        driver="mssql",
    )
    assert compiled.sql == "SELECT * FROM [users] WHERE [user_id]=? AND [name]=?"
    assert compiled.arguments == (4, "Ada")


def test_compiler_expands_foreach_and_preserves_casts_and_literals():
    template = """SELECT ':id', value::text FROM things WHERE id IN (
-- trellis: for item in ids separator=","
:item
-- trellis: endfor
)"""
    compiled = compile_sql(template, {"ids": [3, 5, 8]})
    assert "':id'" in compiled.sql
    assert "value::text" in compiled.sql
    assert compiled.sql.count("$") == 3
    assert compiled.arguments == (3, 5, 8)
    with pytest.raises(TrellisTemplateError):
        compile_sql(template, {"ids": []})

    local_literal = """SELECT
-- trellis: for item in ids separator=","
':item', :item
-- trellis: endfor
"""
    compiled = compile_sql(local_literal, {"ids": [1, 2]})
    assert compiled.sql.count("':item'") == 2
    assert compiled.arguments == (1, 2)


@model
@map("role_id", "role_id", primary_key=True)
@map("role_name", "role_name")
class Role:
    role_id: int
    role_name: str


@model
@map("user_id", "user_id", primary_key=True)
@map("user_name", "user_name")
class User:
    user_id: int
    user_name: str
    roles: list[Role]


def test_mapping_aggregates_and_deduplicates_children():
    rows = [
        {"user_id": 1, "user_name": "Ada", "role_id": 2, "role_name": "admin"},
        {"user_id": 1, "user_name": "Ada", "role_id": 2, "role_name": "admin"},
        {"user_id": 1, "user_name": "Ada", "role_id": 3, "role_name": "reader"},
        {"user_id": 4, "user_name": "Lin", "role_id": None, "role_name": None},
    ]
    users = map_rows(rows, User)
    assert [role.role_name for role in users[0].roles] == ["admin", "reader"]
    assert users[1].roles == []
    with pytest.raises(TrellisCardinalityError):
        map_rows(rows, User, "one")


def test_mapping_returns_dicts_and_scalar_values():
    rows = [{"user_id": 1, "user_name": "Ada"}, {"user_id": 2, "user_name": "Lin"}]
    assert map_rows(rows, dict, "many") == rows
    assert map_rows([rows[0]], dict, "optional") == rows[0]
    assert map_rows([{"total": 2}], int, "one") == 2
    assert map_rows([], int, "optional") is None


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeExecutor:
    def __init__(self):
        self.opened = False
        self.calls = []

    def is_open(self):
        return self.opened

    async def open(self):
        self.opened = True
        return True

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return [{"user_id": args[0], "user_name": "Ada"}]

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        return "UPDATE 1"

    async def executemany(self, sql, args):
        self.calls.append((sql, tuple(args)))

    def transaction(self):
        return FakeTransaction()


class Users(TrellisRepository):
    @select("users/by_id.sql", result=User, cardinality="optional")
    async def by_id(self, user_id: int) -> User | None: ...

    @inline_select("SELECT :expected AS health", result=int, cardinality="one")
    async def health(self, expected: int = 1) -> int: ...

    @inline_command("UPDATE health SET checked = :checked")
    async def mark_checked(self, checked: bool = True) -> str | None: ...

    @command_many("users/rename.sql", items="rows")
    async def rename(self, rows: list[dict[str, object]], audit_user: str) -> None: ...


@pytest.mark.asyncio
async def test_repository_uses_context_and_method_signature(tmp_path):
    config_path = write_config(tmp_path)
    sql = tmp_path / "sql/users/by_id.sql"
    sql.parent.mkdir(parents=True)
    sql.write_text("SELECT user_id, user_name FROM users WHERE user_id=:user_id", encoding="utf-8")
    rename_sql = tmp_path / "sql/users/rename.sql"
    rename_sql.write_text(
        "UPDATE users SET user_name=:name WHERE user_id=:id AND :audit_user IS NOT NULL", encoding="utf-8"
    )
    executor = FakeExecutor()
    async with TrellisContext(config_path, executor=executor) as context:
        result = await Users(context).by_id(7)
        assert result.user_id == 7
        assert await Users(context).health() == 1
        assert await Users(context).mark_checked() == "UPDATE 1"
        assert await context.select_inline("SELECT :value", int, "one", {"value": 9}) == 9
        async with context.transaction():
            pass
        await Users(context).rename(
            [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Lin"}],
            audit_user="collector",
        )
    assert executor.calls[0][1] == (7,)
    assert executor.calls[-1][1] == (("Ada", 1, "collector"), ("Lin", 2, "collector"))


@pytest.mark.asyncio
async def test_command_many_rejects_different_statement_shapes(tmp_path):
    executor = FakeExecutor()
    async with TrellisContext(write_config(tmp_path), executor=executor) as context:
        sql = tmp_path / "sql/conditional.sql"
        sql.parent.mkdir(parents=True)
        sql.write_text("SELECT 1\n-- trellis: if enabled\nWHERE :enabled\n-- trellis: endif\n", encoding="utf-8")
        with pytest.raises(TrellisError, match="same SQL statement"):
            await context.command_many("conditional.sql", [{"enabled": True}, {"enabled": False}])


@pytest.mark.asyncio
async def test_postgres_and_mssql_contexts_can_coexist(tmp_path):
    postgres_executor = FakeExecutor()
    mssql_executor = FakeExecutor()
    postgres_config = write_config(tmp_path, "postgres", "postgres.toml")
    mssql_config = write_config(tmp_path, "mssql", "mssql.toml")
    async with TrellisContext(postgres_config, executor=postgres_executor) as postgres_context:
        async with TrellisContext(mssql_config, executor=mssql_executor) as mssql_context:
            await postgres_context.command_inline("UPDATE users SET user_name=:name", {"name": "Ada"})
            await mssql_context.command_inline("UPDATE users SET user_name=:name", {"name": "Lin"})
    assert postgres_executor.calls[0] == ("UPDATE users SET user_name=$1", ("Ada",))
    assert mssql_executor.calls[0] == ("UPDATE users SET user_name=?", ("Lin",))


def test_generator_renders_models_repositories_and_sql(tmp_path):
    config = TrellisConfig.load(write_config(tmp_path))
    relation = Relation(
        config.tables[0],
        (
            Column("user_id", "integer", "int4", False, None, True, False, True, 1),
            Column("user_name", "character varying", "varchar", False, None, False, False, False, 2),
            Column("email", "character varying", "varchar", False, None, False, False, False, 3),
            Column("nickname", "character varying", "varchar", True, None, False, False, False, 4),
        ),
        "BASE TABLE",
    )
    generator = TrellisGenerator(config)
    models = generator._models([relation])
    repositories = generator._repositories([relation])
    sql = generator._sql(relation)
    compile(models, "generated_models.py", "exec")
    compile(repositories, "generated_repositories.py", "exec")
    assert "class GenUser:" in models
    assert "primary_key=True" in models
    assert "class GenUserRepository" in repositories
    assert "RETURNING" in sql["insert.sql"]
    assert "update_by_primary_key_selective.sql" in sql
    assert '"user_name", "email"' in sql["insert_selective.sql"]
    assert ":model.user_name, :model.email" in sql["insert_selective.sql"]


def test_generator_renders_mssql_crud_sql(tmp_path):
    config = TrellisConfig.load(write_config(tmp_path, "mssql"))
    relation = Relation(
        config.tables[0],
        (
            Column("user_id", "int", "int", False, None, True, False, True, 1),
            Column("user_name", "nvarchar", "nvarchar", False, None, False, False, False, 2),
            Column("nickname", "nvarchar", "nvarchar", True, None, False, False, False, 3),
        ),
        "BASE TABLE",
    )
    sql = TrellisGenerator(config)._sql(relation)
    assert "INSERT INTO [public].[users]" in sql["insert.sql"]
    assert "OUTPUT INSERTED.[user_id]" in sql["insert.sql"]
    assert "RETURNING" not in sql["insert.sql"]
    assert "OUTPUT INSERTED.[user_id]" in sql["update_by_primary_key.sql"]
    assert "WHERE [user_id] = :model.user_id" in sql["update_by_primary_key.sql"]
