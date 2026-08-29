"""Tests for the Trellis data mapper."""

# ruff: noqa: D100, D101, D102, D103, D105, D107

from pathlib import Path

import pytest

from pygarden.trellis import (
    TrellisCardinalityError,
    TrellisConfig,
    TrellisContext,
    TrellisRepository,
    TrellisTemplateError,
    compile_sql,
    inline_command,
    inline_select,
    map,
    map_rows,
    model,
    select,
)
from pygarden.trellis.generator import Column, Relation, TrellisGenerator


def write_config(tmp_path: Path) -> Path:
    config = tmp_path / "trellis.toml"
    config.write_text(
        """
[trellis]
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
    assert config.tables[0].model == "GenUser"
    assert config.resolve_sql("users/select.sql") == tmp_path / "sql/users/select.sql"


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

    def transaction(self):
        return FakeTransaction()


class Users(TrellisRepository):
    @select("users/by_id.sql", result=User, cardinality="optional")
    async def by_id(self, user_id: int) -> User | None: ...

    @inline_select("SELECT :expected AS health", result=int, cardinality="one")
    async def health(self, expected: int = 1) -> int: ...

    @inline_command("UPDATE health SET checked = :checked")
    async def mark_checked(self, checked: bool = True) -> str | None: ...


@pytest.mark.asyncio
async def test_repository_uses_context_and_method_signature(tmp_path):
    config_path = write_config(tmp_path)
    sql = tmp_path / "sql/users/by_id.sql"
    sql.parent.mkdir(parents=True)
    sql.write_text("SELECT user_id, user_name FROM users WHERE user_id=:user_id", encoding="utf-8")
    executor = FakeExecutor()
    async with TrellisContext(config_path, executor=executor) as context:
        result = await Users(context).by_id(7)
        assert result.user_id == 7
        assert await Users(context).health() == 1
        assert await Users(context).mark_checked() == "UPDATE 1"
        assert await context.select_inline("SELECT :value", int, "one", {"value": 9}) == 9
        async with context.transaction():
            pass
    assert executor.calls[0][1] == (7,)


def test_generator_renders_models_repositories_and_sql(tmp_path):
    config = TrellisConfig.load(write_config(tmp_path))
    relation = Relation(
        config.tables[0],
        (
            Column("user_id", "integer", "int4", False, None, True, False, True, 1),
            Column("user_name", "character varying", "varchar", False, None, False, False, False, 2),
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
