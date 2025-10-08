# pyGARDEN Package

Code for the pyGARDEN (**G**eneral **A**pplication **R**esource **D**evelopment **E**nvironment **N**etwork) Python Package to include easy injectable and rich logging, environment checking, and database
connections and query. By default, only SQLite is available as a mixin, but other mixin types to the `Database` class
are Postgres (`[postgres]` extra) or Microsoft SQL Server (`[mssql]` extra). See the [extras](#Extras) section for more
information on how to install these extras, when to choose them, and how to use them.
Some highlights from `pyGARDEN`:

- This package contains an extensible `Database` metaclass with a generic query function that is usable out of the box.
- Everything is configurable with environmental variables -- including email sending, logging, and database connections.

## Installation

### Installation via `uv`

If you have a `uv venv`, you can run the following command in the root of the repo:

`uv pip install -e ".[dev,cli,postgres]"`

You may then need to source your `uv` environment to use the `pygarden` command line interface, e.g. `source .venv/bin/activate`.

Replace the above extras with the extras of your choice.

## Extras

To enable support for specific databases, use the following extras:

- `postgres`: Enables Postgres support via `psycopg2`
- `mssql`: Enables MSSQL support via `pymssql`

#### `pymssql` on MacOS

Before install the `mssql` extra, you may need to install `freetds` using `brew`:

```bash
brew install freetds openssl@3.0
export LDFLAGS="-L/opt/homebrew/opt/freetds/lib -L/opt/homebrew/opt/openssl@3.0/lib"
export CPPFLAGS="-I/opt/homebrew/opt/freetds/include -I/opt/homebrew/opt/openssl@3.0/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/openssl@3.0/lib/pkgconfig"
```

Then, install `pymssql` to your uv environment on its own using:

```bash
uv pip install pymssql==2.2.11 --no-binary :all:
```

After than, you can run `uv sync --extra mssql` or `uv sync --extra all` to get the rest of the dependencies in the group.

### Installation via pip

Run this command to install version 0.3.23 (latest) via pip:

`python3 -m pip --no-cache-dir install pygarden==0.3.25`

This will install latest (not recommended):

`python3 -m pip --no-cache-dir install pygarden`

## Getting the Image

The Docker image for this project is hosted on [Savannah](https://savannah.ornl.gov/),
and is tagged with `savannah.ornl.gov/common/pygarden:${PYTHON_VERSION:-3.12}-latest`,
where `${PYTHON_VERSION:-3.12}` is the Python version you want to use. To pull the
image, you can run:

```bash
docker pull savannah.ornl.gov/common/pygarden:${PYTHON_VERSION:-3.12}-latest
```

## Saving the Image to a Tar File

If you want to save the image to a tar file, you can run:

```bash
docker save savannah.ornl.gov/common/pygarden:${PYTHON_VERSION:-3.12}-latest -o pygarden.tar
gzip pygarden.tar  # optionally compress the tar file
```

Now you can transport the image wherever you'd like!

### Configuration via Environment Variables

Below is a list of environmental variables and what they do:

- DATABASE_TIMEOUT, PG_TIMEOUT: an integer representing the seconds to wait before deciding a timeout occurred.
- DATABASE_DB, PG_DATABASE: a string representing the database to connect to
- DATABASE_USER, PG_USER: a string representing the user to connect to the database as
- DATABASE_PW, PG_PASSWORD: a string representing the password for the DATABASE_USER
- DATABASE_HOST, PG_HOST: a string representing the hostname or IP address hosting the database
- DATABASE_PORT, PG_PORT: an integer representing the port to connect to the database on
- DATABASE_SCHEMA, PG_SCHEMA: a string representing the schema to default to when creating a database connection

These environmental variables have been assigned default values for the Docker container in the file `envfile`, which is called in `docker-compose.yaml` and `docker-compose.test.yaml`

### Creating an extensible Database Python Class

Some `Database` methods such as `query` and `open` rely on
[python mixins](https://www.python.org/dev/peps/pep-0487/), which allow
abstract classes to interact with different types of databases and provide
additional functionality not provided by the `Database` class. Below is an
example of how to create a Database class that uses the PostgresMixin:

```python
from pygarden.mixins.postgres import PostgresMixin
from pygarden.database import Database


class PostgresDatabase(Database, PostgresMixin):
    """The class that allows Database to interact with psycopg2."""
    # TODO add additional functions for your class here, specific to your needs

with PostgresDatabase() as db:
    db.query('SELECT NOW()')
```

### Creating a CRUD table with crud_table.py

```python
from pygarden.mixins.postgres import PostgresMixin
from pygarden.database import Database
from pygarden.crud_table import CRUDTable

# PLEASE NOTE: the name of class MUST be consistent with the name of the
# table in the database itself.
class Users(CRUDTable):
    """Provides CRUD access to the users table"""
    def __init__(self, db):
    """__init__:

    :param db: the database that contains the 'users' table.
    """
    # be sure to define the columns as they appear in the database.
    # in this example, the users table has 6 columns.
    columns = {
        'id': int,
        'email': str,
        'password': str,
    }
    # initialize the super class with the column definition, the schema that
    # the table is in, and the database object.
    super().__init__(columns, schema='public', db)

    # TODO add additional functions for your class here, specific to your needs


class PostgresDatabase(Database, PostgresMixin):
    """The class that allows Database to interact with psycopg2."""
    def __init__(self):
        super().__init__()
        # here we are assigning the CRUD table to the database's 'users'
        # variable and passing the database object to the constructor
        self.users = users(self)
    # TODO add additional functions for your class here, specific to your needs

with PostgresDatabase() as db:
    db.query('SELECT NOW()')

    # this will create a user in the database, with the specified fields and
    # null for the columns not specified
    db.users.create(id=1337, email='admin@test.com', password='*****')

    # this will read the entire user's table 'SELECT * FROM public.users;'
    users_table = db.users.read()

    # this will read only id, and email columns from the users table
    # 'SELECT id, email FROM public.users;'
    columns_users_table = db.users.read(columns=['id', 'email'])

    # data can be read from the database in 'json' format by specifying
    # json=True in your call. The 'json' format returned is a python dictionary
    # that is json serializable
    json_data = db.users.read(json=True)

    # where clauses can be passed as keyword arguments to the call
    # 'SELECT * FROM public.users WHERE id = 1337;
    filtered_users_table = db.users.read(id=1337)

    # to update entries, a where clause must be passed as follows
    # 'UPDATE public.users SET email='update@test.com' WHERE id=1337;'
    db.users.update(where={'id': 1337}, email='update@test.com')

    # to delete entries, a where clause must also be passed. The where clause
    # for a deletion should come in the form of keyword arguments
    # 'DELETE FROM public.users WHERE id=1337;'
    db.users.delete(id=1337)
```

## Testing

The tests for `pygarden` use `pytest` and are available in the `dev` extra.
