#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abstract Database class for connecting to a database.

This class provides an abstract method of interacting with a (by default)
PostgreSQL database. However, the connection parameter may be specified to open
any type of connection through implementation of this abstract class.

The module provides:
- Abstract Database base class with connection management
- Environment variable based configuration
- Context manager support for safe database operations
- Connection information creation and management
- Comprehensive logging and error handling

Examples
--------
Create a database connection::

    >>> db = Database()
    >>> with db as connection:
    ...     results = connection.query("SELECT NOW()")

Create with custom configuration::

    >>> db = Database(connection_info={'dbHost': 'localhost', 'dbPort': 5432})
    >>> db.open()

Use with mixins::

    >>> from pygarden.mixins.postgres import PostgresMixin
    >>> class MyDatabase(PostgresMixin, Database):
    ...     pass
    >>> with MyDatabase() as db:
    ...     results = db.query("SELECT * FROM users")

Notes
-----
This is an abstract base class that should be extended with specific
database mixins to provide actual database functionality.
"""

import traceback
from abc import ABC
from typing import Optional

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class Database(ABC):
    """
    Provides an abstract class for connecting to a database using environmental variables.

    This abstract base class provides a standardized interface for database
    connections with support for different database backends through mixins.
    It handles connection management, logging, and provides context manager
    support.

    :param log_file_info: Dictionary containing log file configuration
    :type log_file_info: dict or None
    :param connection_info: Dictionary containing connection configuration
    :type connection_info: dict or None
    :param **kwargs: Additional keyword arguments

    Attributes
    ----------
    connection_info : dict
        Database connection configuration
    logger : Logger
        Logger instance for this database
    connection : connection or None
        Database connection object
    cursor : cursor or None
        Database cursor object

    Notes
    -----
    Environment Variables for Connection:
        - DATABASE_TIMEOUT, PG_TIMEOUT: Integer seconds to wait before timeout
        - DATABASE_DB, PG_DATABASE: Database name to connect to
        - DATABASE_USER, PG_USER: Database username
        - DATABASE_PW, PG_PASSWORD: Database password
        - DATABASE_HOST, PG_HOST: Database hostname or IP address
        - DATABASE_PORT, PG_PORT: Database port number
        - DATABASE_SCHEMA, PG_SCHEMA: Default database schema
        - DATABASE_ENGINE: Database engine type (default: postgresql)

    Environment Variables for Logging:
        - DATABASE_LOG_PATH: Log file path (default: "")
        - DATABASE_LOG_MODE: Log file mode (default: "a")
        - DATABASE_LOG_ENCODING: Log file encoding (default: "utf-8")

    Examples
    --------
    Basic usage with context manager::

        >>> with Database() as db:
        ...     results = db.query("SELECT * FROM users")

    Custom connection info::

        >>> conn_info = {
        ...     'dbHost': 'localhost',
        ...     'dbPort': 5432,
        ...     'dbName': 'mydb',
        ...     'dbUser': 'user',
        ...     'dbPassword': 'pass'
        ... }
        >>> db = Database(connection_info=conn_info)

    Manual connection management::

        >>> db = Database()
        >>> db.open()
        >>> results = db.query("SELECT NOW()")
        >>> db.close()

    Notes
    -----
    This is an abstract base class that should be extended with specific
    database mixins (e.g., PostgresMixin, SQLiteMixin) to provide actual
    database functionality. The mixins should implement the abstract methods
    like open() and query().
    """

    DEFAULT_DB = ce("DATABASE_DB", ce("PG_DATABASE", "postgres"))
    DEFAULT_USER = ce("DATABASE_USER", ce("PG_USER", "postgres"))
    DEFAULT_PW = ce("DATABASE_PW", ce("PG_PASSWORD", "postgres"))
    DEFAULT_HOST = ce("DATABASE_HOST", ce("PG_HOST", "localhost"))
    DEFAULT_PORT = int(ce("DATABASE_PORT", ce("PG_PORT", 5432)))
    DEFAULT_SCHEMA = ce("DATABASE_SCHEMA", ce("PG_SCHEMA", "public"))
    DEFAULT_ENGINE = ce("DATABASE_ENGINE", "postgresql")
    DEFAULT_TIMEOUT = ce("DATABASE_TIMEOUT", ce("PG_TIMEOUT", 60))
    DEFAULT_LOG_PATH = ce("DATABASE_LOG_FILE", "")
    DEFAULT_LOG_MODE = ce("DATABASE_LOG_MODE", "a")
    DEFAULT_LOG_ENCODING = ce("DATABASE_LOG_ENCODING", "utf-8")
    # define a URI string if URI is preferred to connect
    DEFAULT_URI = f"{DEFAULT_ENGINE}://{DEFAULT_USER}:{str(DEFAULT_PW)}" + f"@{DEFAULT_HOST}/{DEFAULT_DB}"

    def __init__(
        self,
        log_file_info: Optional[dict] = None,
        connection_info: Optional[dict] = None,
        **kwargs,
    ):
        """
        Create a Database object.

        This *does not* open a connection to the database. Use open() or `with` to establish a database connection.

        :param log_file_info: Dictionary containing log file configuration
        :type log_file_info: dict or None
        :param connection_info: Dictionary containing connection configuration
        :type connection_info: dict or None
        :param **kwargs: Additional keyword arguments

        Examples
        --------
        >>> db = Database()
        >>> db = Database(log_file_info={'path': 'db.log'})
        >>> db = Database(connection_info={'dbHost': 'localhost'})

        Notes
        -----
        The constructor initializes the database object but doesn't establish
        a connection. This allows for configuration before connecting.
        """
        if log_file_info is None:
            log_file_info = {
                "path": Database.DEFAULT_LOG_PATH,
                "mode": Database.DEFAULT_LOG_MODE,
                "encoding": Database.DEFAULT_LOG_ENCODING,
            }
        if connection_info is None:
            connection_info = self.create_connection_info()
        if log_file_info["path"] == "":
            self.logger = create_logger()
        else:
            self.logger = create_logger(log_file_info["path"], log_file_info["mode"], log_file_info["encoding"])
        self.connection_info = connection_info
        self.logger.debug(connection_info)
        self.connection = None
        self.cursor = None
        self.logger.debug("Database object successfully initialized")

    def __del__(self):
        """
        Make any pending database commits and close the connection.

        Note that you *should not* rely on this to close connection; you
        should explicitly use close() to sever database connections. That
        is, the python garbage collector is *not guaranteed to run* when
        execution scope would sever the last reference to a Database
        object, nor even when the script finishes execution.

        Examples
        --------
        >>> db = Database()
        >>> del db  # This will call __del__ and close the connection

        Notes
        -----
        This method is called when the object is garbage collected, but
        it's not guaranteed to be called. Always use explicit close() or
        context managers for reliable connection cleanup.
        """
        self.logger.debug("Deleting Database Object")
        self.close()

    def __enter__(self):
        """
        Allow database to be entered via with statement.

        :return: Self reference for context manager
        :rtype: Database

        Examples
        --------
        >>> with Database() as db:
        ...     results = db.query("SELECT NOW()")

        Notes
        -----
        This method automatically opens the database connection when entering
        the context manager.
        """
        self.silent_open()
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """
        Handle database closing when leaving with statement.

        :param err_type: Exception type if an exception occurred
        :type err_type: type or None
        :param err_value: Exception value if an exception occurred
        :type err_value: Exception or None
        :param err_traceback: Exception traceback if an exception occurred
        :type err_traceback: traceback or None

        Notes
        -----
        This method automatically closes the database connection when exiting
        the context manager, regardless of whether an exception occurred.
        """
        self.close()

    def silent_open(self):
        """
        Open database silently without returning anything.

        This method attempts to open the database connection and raises
        an exception if it fails.

        :raises BaseException: If the database cannot be opened

        Examples
        --------
        >>> db = Database()
        >>> db.silent_open()  # Opens connection, raises exception if it fails

        Notes
        -----
        This method is used internally by the context manager and doesn't
        return any value. It either succeeds silently or raises an exception.
        """
        try:
            state = self.open()
        except BaseException as e:
            traceback.print_stack()
            self.logger.error(f"Error {e} occurred while entering Database")
            state = False
        if state is True:
            return
        if state is False:
            traceback.print_stack()
            self.logger.critical("Not possible to enter Database")
            raise BaseException("Not possible to enter Database")

    def close(self):
        """
        Explicitly close the connection.

        This method closes both the cursor and connection, ensuring
        proper cleanup of database resources.

        :return: Always returns None
        :rtype: None

        Examples
        --------
        >>> db = Database()
        >>> db.open()
        >>> db.close()  # Explicitly close the connection

        Notes
        -----
        This method safely closes both the cursor and connection, and
        commits any pending transactions before closing.
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.connection:
            self.connection.commit()
            self.connection.close()
            self.connection = None

    def is_open(self):
        """
        Determine if the database is open or not.

        :return: True if both connection and cursor are active, False otherwise
        :rtype: bool

        Examples
        --------
        >>> db = Database()
        >>> db.is_open()
        False
        >>> db.open()
        >>> db.is_open()
        True
        >>> db.close()
        >>> db.is_open()
        False

        Notes
        -----
        This method checks if both the connection and cursor objects are
        not None, indicating an active database connection.
        """
        if self.cursor is not None and self.connection is not None:
            return True  # If both are on, return True
        # If one or both connection and cursor are missing, return False
        return False

    def override_connection(self, connection):
        """
        Override the default connection.

        This is useful for using other connections than `psycopg2` for downstream development.

        :param connection: Any type of database connection object
        :type connection: any

        Examples
        --------
        >>> db = Database()
        >>> custom_conn = some_other_db_library.connect()
        >>> db.override_connection(custom_conn)

        Notes
        -----
        This method allows you to use custom database connection objects
        instead of the default connection type. Useful for testing or
        when using different database libraries.
        """
        self.connection = connection

    def modify_connection_info(self, variable, value):
        """
        Modify a `variable` and set it to `value` in the connection_info attribute.

        :param variable: The connection variable to set
        :type variable: str
        :param value: The value for the connection variable
        :type value: any

        Examples
        --------
        >>> db = Database()
        >>> db.modify_connection_info('dbHost', 'new-host')
        >>> db.modify_connection_info('dbPort', 5433)

        Notes
        -----
        This method allows you to modify connection parameters after the
        database object has been created but before connecting.
        """
        self.connection_info[variable] = value

    @staticmethod
    def create_connection_info(
        db_name=None,
        db_user=None,
        db_password=None,
        db_host=None,
        db_port=None,
        db_schema=None,
        db_type=None,
        db_engine=None,
        db_timeout=None,
    ):
        """
        Create the complete connection_info dictionary to use for database connection.

        This method generates a dictionary containing all the necessary information for
        establishing a connection to a database. It constructs the connection URI based
        on the provided parameters and defaults to certain values if parameters are not
        provided.

        :param db_name: The name of the database
        :type db_name: str or None
        :param db_user: The database user
        :type db_user: str or None
        :param db_password: The password for the database user
        :type db_password: str or None
        :param db_host: The host where the database is located
        :type db_host: str or None
        :param db_port: The port on which the database is listening
        :type db_port: int or None
        :param db_schema: The schema to use within the database
        :type db_schema: str or None
        :param db_type: The type of the database (e.g., 'postgres', 'mssql')
        :type db_type: str or None
        :param db_engine: The SQLAlchemy database engine string
        :type db_engine: str or None
        :param db_timeout: The timeout setting for the database connection
        :type db_timeout: int or None
        :return: Complete connection information dictionary
        :rtype: dict

        Examples
        --------
        Create connection info with defaults::

            >>> info = Database.create_connection_info()
            >>> print(info['dbHost'])
            localhost

        Create connection info with custom values::

            >>> info = Database.create_connection_info(
            ...     db_host='myhost.com',
            ...     db_port=5433,
            ...     db_name='mydb'
            ... )
            >>> print(info['dbHost'])
            myhost.com

        Create SQLite connection info::

            >>> info = Database.create_connection_info(
            ...     db_type='sqlite',
            ...     db_name='test.db'
            ... )
            >>> print(info['dbEngine'])
            sqlite

        Notes
        -----
        This method automatically determines the database engine based on
        the db_type parameter if db_engine is not provided. It supports
        PostgreSQL, SQLite, MSSQL, and InfluxDB.
        """
        if db_type and not db_engine:
            if db_type.startswith("postgres") or db_type.startswith("pg"):
                db_engine = "postgresql"
            elif db_type.startswith("mssql"):
                db_engine = "mssql+pymssql"
            elif db_type.startswith("influx"):
                db_engine = "influxdb"
            elif db_type.startswith("sqlite"):
                db_engine = "sqlite"
        if db_engine is not None and db_engine.startswith("sqlite"):
            uri = f"{db_engine}://{db_name}"
        else:
            engine = db_engine or Database.DEFAULT_ENGINE
            user = db_user or Database.DEFAULT_USER
            password = db_password or Database.DEFAULT_PW
            host = db_host or Database.DEFAULT_HOST
            port = db_port or Database.DEFAULT_PORT
            name = db_name or Database.DEFAULT_DB
            uri = f"{engine}://{user}:{password}@{host}:{port}/{name}"

        connection_info = {
            "dbName": db_name if db_name is not None else Database.DEFAULT_DB,
            "dbUser": db_user if db_user is not None else Database.DEFAULT_USER,
            "dbPassword": db_password if db_password is not None else Database.DEFAULT_PW,
            "dbHost": db_host if db_host is not None else Database.DEFAULT_HOST,
            "dbPort": db_port if db_port is not None else Database.DEFAULT_PORT,
            "dbTimeout": db_timeout if db_timeout is not None else Database.DEFAULT_TIMEOUT,
            "dbSchema": db_schema if db_schema is not None else Database.DEFAULT_SCHEMA,
            "dbEngine": db_engine if db_engine is not None else Database.DEFAULT_ENGINE,
            "uri": uri,
        }
        return connection_info
