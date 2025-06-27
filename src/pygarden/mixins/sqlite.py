#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide SQLite database mixin.

This module provides a SQLiteMixin class that extends the base Database
class to provide SQLite-specific functionality. It handles connection
management, query execution, and SQLite-specific features.

Examples
--------
Create a SQLite database class:
    >>> class MyDatabase(SQLiteMixin, Database):
    ...     pass
    >>> 
    >>> with MyDatabase() as db:
    ...     results = db.query("SELECT sqlite_version()")

Use with custom database file:
    >>> db = SQLiteMixin(connection_info={
    ...     'dbName': '/path/to/database.db'
    ... })
"""
import sqlite3
from typing import Any, List, Optional, Tuple

from pygarden.database import Database
from pygarden.logz import create_logger


class SQLiteMixin(Database):
    """
    SQLite database mixin.

    This mixin provides SQLite-specific functionality for the Database
    class. It handles connection management, query execution, and provides
    SQLite-specific features like file-based storage and transaction
    management.

    Parameters
    ----------
    connection_info : dict or None, optional
        Database connection configuration, by default None
    **kwargs
        Additional keyword arguments passed to Database

    Attributes
    ----------
    connection : sqlite3.Connection or None
        SQLite connection object
    cursor : sqlite3.Cursor or None
        Database cursor object
    logger : Logger
        Logger instance for this database

    Notes
    -----
    Environment Variables:
        - DATABASE_DB: Database file path (default: ':memory:')
        - DATABASE_TIMEOUT: Connection timeout in seconds

    Examples
    --------
    Basic usage:
        >>> class MyDatabase(SQLiteMixin, Database):
        ...     pass
        >>> 
        >>> with MyDatabase() as db:
        ...     results = db.query("SELECT * FROM users")

    In-memory database:
        >>> db = SQLiteMixin(connection_info={'dbName': ':memory:'})
        >>> db.open()

    File-based database:
        >>> db = SQLiteMixin(connection_info={'dbName': 'data.db'})
        >>> db.open()
    """

    def __init__(self, connection_info: Optional[dict] = None, **kwargs):
        """
        Initialize the SQLite mixin.

        Parameters
        ----------
        connection_info : dict or None, optional
            Database connection configuration, by default None
        **kwargs
            Additional keyword arguments passed to Database

        Examples
        --------
        >>> db = SQLiteMixin()
        >>> db = SQLiteMixin(connection_info={'dbName': 'test.db'})
        """
        super().__init__(connection_info=connection_info, **kwargs)
        self.connection = None
        self.cursor = None
        self.logger = create_logger()

    def open(self) -> bool:
        """
        Open a connection to the SQLite database.

        This method establishes a connection to the SQLite database
        using the configuration provided in connection_info.

        Returns
        -------
        bool
            True if connection is successful, False otherwise

        Examples
        --------
        >>> db = SQLiteMixin()
        >>> success = db.open()
        >>> print(success)
        True
        """
        try:
            db_name = self.connection_info.get("dbName", ":memory:")
            timeout = self.connection_info.get("dbTimeout", 30)
            
            self.connection = sqlite3.connect(
                db_name,
                timeout=timeout,
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            self.logger.info(f"Successfully connected to SQLite database: {db_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to SQLite: {e}")
            return False

    def close(self) -> None:
        """
        Close the SQLite database connection.

        This method safely closes the database connection and cursor,
        ensuring proper cleanup of resources.

        Examples
        --------
        >>> db = SQLiteMixin()
        >>> db.open()
        >>> db.close()  # Explicitly close the connection
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.connection:
            self.connection.close()
            self.connection = None

    def query(self, query: str, params: Optional[Tuple] = None) -> List[dict]:
        """
        Execute a SQL query and return results.

        This method executes a SQL query with optional parameters and
        returns the results as a list of dictionaries.

        Parameters
        ----------
        query : str
            The SQL query to execute
        params : tuple or None, optional
            Parameters for the query, by default None

        Returns
        -------
        list
            List of dictionaries containing query results

        Examples
        --------
        Simple query:
            >>> with SQLiteMixin() as db:
            ...     results = db.query("SELECT * FROM users")
            ...     print(len(results))

        Parameterized query:
            >>> with SQLiteMixin() as db:
            ...     results = db.query(
            ...         "SELECT * FROM users WHERE age > ?",
            ...         params=(18,)
            ...     )
            ...     print(results)
        """
        try:
            if not self.is_open():
                self.open()

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in self.cursor.fetchall()]
            else:
                self.connection.commit()
                return []

        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.connection.rollback()
            return []

    def execute_many(self, query: str, params_list: List[Tuple]) -> bool:
        """
        Execute a query multiple times with different parameters.

        This method is useful for bulk insert, update, or delete operations
        where the same query needs to be executed with different parameter sets.

        Parameters
        ----------
        query : str
            The SQL query to execute
        params_list : list
            List of parameter tuples for each execution

        Returns
        -------
        bool
            True if successful, False otherwise

        Examples
        --------
        Bulk insert:
            >>> users = [
            ...     ('John', 25),
            ...     ('Jane', 30),
            ...     ('Bob', 35)
            ... ]
            >>> with SQLiteMixin() as db:
            ...     success = db.execute_many(
            ...         "INSERT INTO users (name, age) VALUES (?, ?)",
            ...         users
            ...     )
            ...     print(success)
            True
        """
        try:
            if not self.is_open():
                self.open()

            self.cursor.executemany(query, params_list)
            self.connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Bulk execution failed: {e}")
            self.connection.rollback()
            return False

    def get_table_names(self) -> List[str]:
        """
        Get a list of all table names in the database.

        Returns
        -------
        list
            List of table names

        Examples
        --------
        >>> with SQLiteMixin() as db:
        ...     tables = db.get_table_names()
        ...     print(tables)
        ['users', 'orders', 'products']
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        results = self.query(query)
        return [row['name'] for row in results]

    def get_column_info(self, table_name: str) -> List[dict]:
        """
        Get column information for a specific table.

        Parameters
        ----------
        table_name : str
            Name of the table

        Returns
        -------
        list
            List of dictionaries containing column information

        Examples
        --------
        >>> with SQLiteMixin() as db:
        ...     columns = db.get_column_info('users')
        ...     for col in columns:
        ...         print(f"{col['name']}: {col['type']}")
        id: INTEGER
        name: TEXT
        email: TEXT
        """
        query = "PRAGMA table_info(?)"
        return self.query(query, (table_name,))

    def is_open(self):
        """Check if the database connection is open."""
        return self.connection and self.cursor
