# Trellis

**Trellis** stands for **Typed Result & Execution Layer for Lightweight Integrated SQL**.

Trellis is pyGARDEN's async, external-SQL data mapper. It generates typed
dataclasses and CRUD repositories from a live PostgreSQL schema while keeping
custom SQL in ordinary `.sql` files.

Install it with:

```bash
pip install "pygarden[trellis]"
```

## Configuration and generation

Create `trellis.toml` in the application root:

```toml
[trellis]
sql_path = "sql"

[trellis.generate]
models_output = "src/example/models/generated.py"
repositories_output = "src/example/repositories/generated.py"
sql_output = "sql/generated"
# Add import statements needed by configured python_type overrides.
imports = ["from example.types import AccountStatus"]

[[trellis.tables]]
schema = "public"
table = "users"
model = "GenUser"
repository = "GenUserRepository"
```

Generate against the database configured by pyGARDEN's existing `DATABASE_*`
or `PG_*` environment variables:

```bash
pygarden trellis generate --config trellis.toml
pygarden trellis generate --config trellis.toml --check
```

Generated files carry a marker and are safe to regenerate. Trellis refuses to
overwrite an existing file without that marker. Keep application extensions in
separate modules and subclass the generated model or repository.

## Context and repositories

A `TrellisContext` owns one asyncpg connection. Repositories using the same
context share that connection and its transaction:

```python
from pygarden.trellis import TrellisContext

async with TrellisContext("trellis.toml") as context:
    users = UserRepository(context)
    roles = RoleRepository(context)

    async with context.transaction():
        user = await users.insert(new_user)
        await roles.assign_user_role(user.user_id, role_id)
```

Create a context per unit of work; do not share one context concurrently across
requests. Pool-backed execution is intentionally left to a later executor.

## Custom SQL

Custom methods are typed async methods whose bodies are supplied by a
decorator:

```python
from pygarden import trellis


class UserRepository(GenUserRepository):
    @trellis.select("users/active.sql", result=User, cardinality="many")
    async def active_users(self, active_only: bool = True) -> list[User]:
        ...
```

Values use named binds. Trellis converts them to asyncpg positional binds; it
never interpolates values directly:

```sql
SELECT user_id, user_name
FROM users
-- trellis: if active_only
WHERE active_date IS NOT NULL AND active_date <= now()
-- trellis: endif
```

The available directives are `if`/`elif`/`else`/`endif`,
`choose`/`when`/`otherwise`/`endchoose`, and
`for item in items separator=","`/`endfor`. Conditions support safe Python-like
boolean expressions, comparisons, membership, dotted access, and `None`
checks. Empty loops raise an error unless an enclosing `if` excludes them.

## Inline SQL

Use an explicit inline API for small statements such as health checks. This
keeps file-backed SQL unambiguous while still using Trellis parameter binding
and result mapping:

```python
async with TrellisContext("trellis.toml") as context:
    value = await context.select_inline(
        "SELECT 1",
        result_type=int,
        cardinality="one",
    )
    healthy = value == 1
```

Inline statements can also define typed repository methods:

```python
class HealthRepository(TrellisRepository):
    @trellis.inline_select("SELECT 1", result=int, cardinality="one")
    async def check(self) -> int:
        ...
```

Named parameters work the same way as external SQL:

```python
result = await context.select_inline(
    "SELECT :expected::int",
    result_type=int,
    cardinality="one",
    parameters={"expected": 1},
)
```

Use `context.command_inline(sql, parameters)` or
`@trellis.inline_command(sql)` for an inline statement that does not return
rows. Inline SQL supports the same comment directives as `.sql` files. Values
are always bound; inline SQL does not enable raw string interpolation.

## Dictionary and scalar results

Queries do not need a generated model. Use `result=dict` to return each row as
a dictionary whose keys are the selected column names or aliases:

```python
class UserReportRepository(TrellisRepository):
    @trellis.select("reports/user_summary.sql", result=dict, cardinality="many")
    async def user_summary(self, active_only: bool = False) -> list[dict[str, object]]:
        ...
```

With `cardinality="one"`, the same result declaration returns one dictionary;
with `cardinality="optional"`, it returns either one dictionary or `None`.

For a query that selects one value, provide its Python type. Trellis takes the
first selected column from the row and applies the requested cardinality:

```sql
SELECT COUNT(*)::int AS total
FROM users;
```

```python
class UserRepository(GenUserRepository):
    @trellis.select("users/count.sql", result=int, cardinality="one")
    async def count_users(self) -> int:
        ...
```

Scalar queries can use `str`, `int`, `float`, `bool`, or another application
type returned by the database driver. Select only one column so the intended
value is unambiguous.

## Joined results

`@trellis.model` creates a keyword-only dataclass and `@trellis.map` associates
fields with result columns. Generated primary-key metadata lets Trellis collapse
flat joined rows and deduplicate one-to-many children:

```python
@trellis.model
@trellis.map("is_active", "is_active")
class User(GenUser):
    roles: list[GenRole]
    is_active: bool
```

An outer-joined child whose key fields are all `NULL` is omitted. Version 1
supports one collection nesting level.

Trellis has no SQLAlchemy dependency. Its compiler, executor, and result mapper
are separated so a SQLAlchemy adapter can be added later without changing SQL
files or model metadata.
