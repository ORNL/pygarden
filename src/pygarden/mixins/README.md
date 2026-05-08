# PyGarden Mixins

This directory contains various mixins for database connections and other functionality.

## Database Mixins

The pygarden database mixins make handling database connections much easier. When set up with ENV variables properly, a
developer simply needs to worry about queries and spending less time managing connections and cursors.

### Installing mixin dependencies

Some mixins are available without extra dependencies, while others require
optional extras from `pygarden`:

- `SQLiteMixin`: no extra required
- `PostgresMixin` and `AsyncPostgresMixin`: `pygarden[postgres]`
- `MSSQLMixin`: `pygarden[mssql]`
- `DuckDBMixin`: `pygarden[duckdb]`
- `PandasMixin`: `pygarden[db-pandas]`
- `InfluxMixin`: `pygarden[influx]`

Examples:

```bash
uv pip install "pygarden[postgres]"
uv pip install "pygarden[duckdb]"
uv pip install "pygarden[mssql,db-pandas]"
```

### PostgresMixin

Synchronous PostgreSQL connection using psycopg.

To get started with the PostgreSQL mixin for pygarden, install pygarden with the PostgreSQL mixin:

```bash
uv pip install "pygarden[postgres]"
```
To make the proper database connection, the pygarden PostgreSQL mixin uses pygarden's `check_environment()` function to 
find the ENV variables for the different segments of a database connection string. If these are not provided, defaults are then used:

```bash
DEFAULT_DB = ce("DATABASE_DB_PG", ce("DATABASE_DB", ce("PG_DATABASE", "postgres")))
DEFAULT_USER = ce("DATABASE_USER_PG", ce("DATABASE_USER", ce("PG_USER", "postgres")))
DEFAULT_PW = ce("DATABASE_PW_PG", ce("DATABASE_PW", ce("PG_PASSWORD", "postgres")))
DEFAULT_HOST = ce("DATABASE_HOST_PG", ce("DATABASE_HOST", ce("PG_HOST", "localhost")))
DEFAULT_PORT = int(ce("DATABASE_PORT_PG", ce("DATABASE_PORT", ce("PG_PORT", 5432))))
DEFAULT_TIMEOUT = ce("DATABASE_TIMEOUT", ce("PG_TIMEOUT", 60))
DEFAULT_SCHEMA = ce("DATABASE_SCHEMA_PG", ce("DATABASE_SCHEMA", ce("PG_SCHEMA", "public")))
DEFAULT_ENGINE = ce("DATABASE_ENGINE_PG", ce("DATABASE_ENGINE", "postgresql"))
DEFAULT_SEARCH_PATH = ce("DATABASE_SEARCH_PATH", "public")
DEFAULT_APPLICATION_NAME = ce("DATABASE_APPLICATION_NAME", "pygarden")
```

Generally these would be set in a Dockerfile, or a gitlab-ci.yml file, or another file proper for setting ENV variables.

With ENV variables set up and postgres installed locally or in a container, make a simple Database class importing Database and 
PostgresMixin from pygarden:

```python
from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin
from pygarden.logz import create_logger

logger = create_logger()

class TestDB(Database, PostgresMixin):
    def __init__(self, **kwargs):
        super().__init__()
```

Calling `super().__init__()` the class takes care of the connection and cursor opening and closing.

From here, you can write queries that can be called later. What is returned is a generator representing a list of dictionairies 
corresponding to each row in the database. Likewise, you may write queries that insert as well:

```python
from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin
from pygarden.logz import create_logger

logger = create_logger()


class TestDB(Database, PostgresMixin):
    def __init__(self, **kwargs):
        super().__init__()


    def get_users(self):
        return self.query("SELECT * FROM public.users;")

    def insert_user(self, first_name, last_name, email):
        self.cursor.execute("""INSERT INTO public.users (first_name, last_name, email)
                        VALUES (%s, %s, %s);""")
```

Now in your code, you can call these queries like so (given this test database file is called test_database):

```python

from test_database import TestDB

with TestDB() as db:
    users = db.get_users()

print(list(users))

# output
[
    {'id': 1019, 'first_name': 'Mister', 'last_name': 'Man', 'email': 'some_email@email.com'},
    {'id': 1016, 'first_name': 'That', 'last_name': 'Guy', 'email': 'That_guys_email@that_guy.com'},
    {'id': 1132, 'first_name': 'Who', 'last_name': 'Dis', 'email': 'new_email@whodis.com}
]

# insert
with TestDB() as db:
    db.insert_user('Johnny', 'Rotten', 'god_save_the_queen@punk_rock.com')
```


### AsyncPostgresMixin

Asynchronous PostgreSQL connection using asyncpg. Provides async/await support for high-performance database operations.

**Features:**
- Async connection management
- Parameterized queries with proper escaping
- Multiple query methods: `query()`, `execute()`, `fetch()`, `fetchval()`, `fetchrow()`
- Dictionary result support
- Automatic connection handling

**Example Usage:**
```python
import asyncio
from pygarden.mixins import AsyncPostgresMixin

class MyAsyncDB(AsyncPostgresMixin):
    def __init__(self):
        self.connection_info = {
            "dbName": "my_db",
            "dbUser": "user",
            "dbPassword": "password",
            "dbHost": "localhost",
            "dbPort": 5432
        }

async def main():
    db = MyAsyncDB()
    await db.open()
    
    # Execute queries
    await db.execute("INSERT INTO users (name) VALUES ($1)", "John")
    users = await db.query("SELECT * FROM users")
    
    await db.close()

asyncio.run(main())
```

### SQLiteMixin

Synchronous SQLite connection. No extra is required.

### MSSQLMixin

Synchronous Microsoft SQL Server connection. Install with `pygarden[mssql]`.

### DuckDBMixin

Synchronous DuckDB connection. Install with `pygarden[duckdb]`.

## Other Mixins

### PostgresLoggerMixin
Provides a quick and easy way to log information to both the terminal and the database.

All one needs to initiate the PostgresLogger class is a schema name, then they would call the log just like they would normally:

```python
from pygarden.database import Database

db_log = PostgresLogger(self.workspace)
db_log.info("This is a log message", w=True)
```

This will log an INFO level log message and attempt to write it to the database.

**Features:**
- Passing the `-w` flag will log the message to the log table of a schema in the database.
- Passing the `-c` flag will add the log to an internal list with the intent being to dump all of the logs in the database later. For example, if you have a running loop and want to log absolutely everything, but don't want to open and close a database connection through every iteration, simply pass the `-c` flag to your log method, and after your loop, run the `write_log_collection_to_database()`. This logs all messages in the list and clears the log collection, `self.log_collection`. Note that this can be leveraged without using the logger, just pass `write_log_collection_to_database()` a list of tuples representing log messages.

**NOTE:** Logging provides overhead, so logging a lot of information in long running loops will slow down your functions. Just keep this in mind when deciding what you want to log.

### MinioMixin
Object storage operations using MinIO.

### InfluxMixin

Time-series database operations using InfluxDB.

### PandasMixin

Data manipulation operations using pandas. Install with `pygarden[db-pandas]`.

### MultipleMixin
Support for multiple database connections.

Example Usage: 
```python
from pygarden.mixins.multiple import MultiDatabase
import os 

postgres_db1 = {'id': 'pgdb1', 'type': 'postgres', 'host': 'db.ornl.gov', 'port': '5435', 'database': 'db1', 'user': os.getenv('pgdb1_user'), 'password': os.getenv('pgdb1_password')}
postgres_db2 = {'id': 'pgdb2', 'type': 'postgres', 'host': 'localhost', 'port': '5432', 'database': 'db2', 'user': os.getenv('pgdb2_user'), 'password': os.getenv('pgdb2_password')}
mssql_db = {'id': 'mssql', 'type': 'mssql', 'host': 'localhost', 'port': '1433', 'database': 'mssql', 'user': os.getenv('mssql_user'), 'password': os.getenv('mssql_password')}

config = [postgres_db1, postgres_db2, mssql_db]

multi = MultiDatabase(configs)

multi.query('SELECT 1;') # Queries all databases in multi

multi.databases['pgdb1'].query('SELECT 1;') # query a specific database by id

```

### APITestMixin
API GET/POST test helper.

Example Usage:
```python
from pygarden.mixins.api_test_mixin import BooleanValue, APITestMixin

class TestSuite(APITestMixin):
    def __init__(self):
        super().__init__("https://dog.ceo/api")
        self.verify_ssl = True
    
    def get_random_image(self) -> dict:
        return self.get("breeds/image/random").json()
    
    def is_status_successful(self, random_image_response) -> bool:
        return random_image_response["status"] == "success"
    
    def is_status_unsuccessful(self, random_image_response) -> bool:
        return random_image_response["status"] == "error"
    
    def run_full_tests(self):
        rir = self.run_test(self.get_random_image, dict, "Got Random Image Response: {VAL}")
        self.run_test(self.is_status_successful, BooleanValue(True), "Status is Successful", rir)
        self.run_test(self.is_status_unsuccessful, BooleanValue(True), "Status is Unsuccessful", rir)

if __name__ == "__main__":
    ts = TestSuite()
    print("Running API Tests...", flush=True)
    TestSuite.print_line_separator()
    ts.run_full_tests()
```
Example Output:
```
Running API Tests...
████████████████████████████████████████████████████████████████████████████████
Got Random Image Response: {'message': 'https://images.dog.ceo/breeds/terrier-silky/n02097658_4890.jpg', 'status': 'success'}
Status is Successful
is_status_unsuccessful did not return the right value, it returned False instead of True
```
