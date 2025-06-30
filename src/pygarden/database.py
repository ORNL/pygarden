#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abstract Database class for connecting to a database.

This class provides an abstract method of interacting with a (by default)
PostgreSQL database. However, the connection parameter may be specified to open
any type of connection through implementation of this abstract class.

**Environment Variables:**
    DATABASE_DB, PG_DATABASE: Database name (default: postgres)
    DATABASE_USER, PG_USER: Database user (default: postgres)
    DATABASE_PW, PG_PASSWORD: Database password (default: postgres)
    DATABASE_HOST, PG_HOST: Database host (default: localhost)
    DATABASE_PORT, PG_PORT: Database port (default: 5432)
    DATABASE_SCHEMA, PG_SCHEMA: Database schema (default: public)
    DATABASE_ENGINE: Database engine (default: postgresql)
    DATABASE_TIMEOUT, PG_TIMEOUT: Connection timeout in seconds (default: 60)
    DATABASE_LOG_FILE: Log file path (default: "")
    DATABASE_LOG_MODE: Log file mode (default: a)
    DATABASE_LOG_ENCODING: Log file encoding (default: utf-8)

**Usage Example:**
    >>> with Database() as db:
    ...     db.cursor.execute("SELECT 1")
    ...     result = db.cursor.fetchone()
"""
import traceback
from abc import ABC
from typing import Optional

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

class Database(ABC):
    """
    Abstract base class for database connections using environmental variables.

    This class provides a standardized interface for database connections with
    automatic configuration from environment variables. It supports connection
    management, logging, and context manager functionality.

    **Attributes:**
        connection_info (dict): Database connection parameters.
        logger: Logger instance for database operations.
        connection: Database connection object (set after opening).
        cursor: Database cursor object (set after opening).

    **Usage Notes:**
        - Use as a context manager with 'with' statement for automatic cleanup.
        - Connection is not opened automatically on initialization.
        - All operations are logged if logging is configured.
        - Subclasses must implement the abstract 'open' method.

    **Example:**
        >>> class PostgreSQLDatabase(Database):
        ...     def open(self):
        ...         # Implementation specific to PostgreSQL
        ...         pass
        >>> with PostgreSQLDatabase() as db:
        ...     db.cursor.execute("SELECT version()")
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
        Initialize a Database object.

        This *does not* open a connection to the database. Use open() or `with` to establish a database connection.

        :param log_file_info: A dictionary containing log file info.
        :type log_file_info: dict, optional
        :param connection_info: A dictionary containing connection info.
        :type connection_info: dict, optional
        :param kwargs: Additional keyword arguments passed to create_connection_info.
        :note:
            If log_file_info is None, uses default logging configuration.
            If connection_info is None, calls create_connection_info with kwargs.
            If log_file_info path is empty, creates a logger without file output.
        :example:
            >>> db = Database(connection_info={'host': 'localhost', 'port': 5432})
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
        Cleanup method called when the object is garbage collected.

        Make any pending database commits and close the connection.

        :note:
            You *should not* rely on this to close connection; you
            should explicitly use close() to sever database connections. That
            is, the python garbage collector is *not guaranteed to run* when
            execution scope would sever the last reference to a Database
            object, nor even when the script finishes execution.
        :side effects: Calls self.close() to cleanup database resources.
        """
        self.logger.debug("Deleting Database Object")
        self.close()

    def __enter__(self):
        """
        Context manager entry method.

        Allow database to be entered via with statement.

        :return: The database instance.
        :rtype: Database
        :side effects: Calls silent_open() to establish database connection.
        :example:
            >>> with Database() as db:
            ...     db.cursor.execute("SELECT 1")
        """
        self.silent_open()
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """
        Context manager exit method.

        Handle database closing when leaving with statement.

        :param err_type: The exception type.
        :type err_type: type, optional
        :param err_value: The exception value.
        :type err_value: Exception, optional
        :param err_traceback: The exception traceback.
        :type err_traceback: traceback, optional
        :side effects: Calls self.close() to cleanup database resources.
        """
        self.close()

    def silent_open(self):
        """
        Open database silently without returning anything.

        This method attempts to open the database connection and raises
        an exception if it fails. Used internally by the context manager.

        :raises BaseException: If the database cannot be opened.
        :side effects: Attempts to open database connection via self.open().
        :note:
            If opening fails, prints the traceback and raises an exception.
            This method is called automatically by the context manager.
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
        Explicitly close the database connection.

        This method closes both the cursor and connection, ensuring
        proper cleanup of database resources.

        :side effects: Closes cursor and connection, commits any pending transactions.
        :note:
            Always commits the connection before closing to ensure data persistence.
            Sets both cursor and connection to None after closing.
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
        Check if the database connection is open.

        Determine if the database is open or not by checking both cursor and connection.

        :return: True if both cursor and connection exist, False otherwise.
        :rtype: bool
        :example:
            >>> db = Database()
            >>> db.is_open()
            False
            >>> db.open()
            >>> db.is_open()
            True
        """
        if self.cursor is not None and self.connection is not None:
            return True  # If both are on, return True
        # If one or both connection and cursor are missing, return False
        return False

    def override_connection(self, connection):
        """
        Override the default connection with a custom one.

        This is useful for using other connections than `psycopg2` for downstream development.

        :param connection: Any type of database connection object.
        :type connection: object
        :side effects: Sets self.connection to the provided connection object.
        :note:
            This bypasses the normal connection creation process.
            Useful for testing or when using custom connection objects.
        """
        self.connection = connection

    def modify_connection_info(self, variable, value):
        """
        Modify a connection parameter in the connection_info attribute.

        :param variable: The connection variable to set.
        :type variable: str
        :param value: The value to set for the variable.
        :type value: Any
        :side effects: Updates the connection_info dictionary.
        :note:
            This modifies the connection parameters but does not affect
            an already established connection. A new connection must be
            opened to use the modified parameters.
        :example:
            >>> db = Database()
            >>> db.modify_connection_info('host', 'newhost.com')
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
        Create a connection info dictionary from parameters or environment variables.

        :param db_name: Database name (default: from environment).
        :type db_name: str, optional
        :param db_user: Database user (default: from environment).
        :type db_user: str, optional
        :param db_password: Database password (default: from environment).
        :type db_password: str, optional
        :param db_host: Database host (default: from environment).
        :type db_host: str, optional
        :param db_port: Database port (default: from environment).
        :type db_port: int, optional
        :param db_schema: Database schema (default: from environment).
        :type db_schema: str, optional
        :param db_type: Database type (default: from environment).
        :type db_type: str, optional
        :param db_engine: Database engine (default: from environment).
        :type db_engine: str, optional
        :param db_timeout: Connection timeout (default: from environment).
        :type db_timeout: int, optional
        :return: Dictionary containing connection parameters.
        :rtype: dict
        :note:
            If any parameter is None, uses the corresponding environment variable.
            All parameters are optional and have sensible defaults.
        :example:
            >>> info = Database.create_connection_info(db_host='localhost', db_port=5432)
            >>> print(info['host'])
            localhost
        """
        return {
            "db_name": db_name or Database.DEFAULT_DB,
            "db_user": db_user or Database.DEFAULT_USER,
            "db_password": db_password or Database.DEFAULT_PW,
            "db_host": db_host or Database.DEFAULT_HOST,
            "db_port": db_port or Database.DEFAULT_PORT,
            "db_schema": db_schema or Database.DEFAULT_SCHEMA,
            "db_type": db_type or Database.DEFAULT_ENGINE,
            "db_engine": db_engine or Database.DEFAULT_ENGINE,
            "db_timeout": db_timeout or Database.DEFAULT_TIMEOUT,
        }
