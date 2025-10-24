# PyGarden Mixins

This directory contains various mixins for database connections and other functionality.

## Database Mixins

### PostgresMixin
Synchronous PostgreSQL connection using psycopg2.

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
Synchronous SQLite connection.

### MSSQLMixin
Synchronous Microsoft SQL Server connection.

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
Data manipulation operations using pandas.

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

\```