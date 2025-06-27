#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide PostgreSQL database mixin.

This module provides a PostgresMixin class that extends the base Database
class to provide PostgreSQL-specific functionality. It handles connection
management, query execution, and PostgreSQL-specific features.

Examples
--------
Create a PostgreSQL database class:
    >>> class MyDatabase(PostgresMixin, Database):
    ...     pass
    >>> 
    >>> with MyDatabase() as db:
    ...     results = db.query("SELECT NOW()")

Use with custom connection info:
    >>> db = MyDatabase(connection_info={
    ...     'dbHost': 'localhost',
    ...     'dbPort': 5432,
    ...     'dbName': 'mydb'
    ... })
"""
import logging
import traceback
from typing import Any, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from pygarden.database import Database
from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class PostgresMixin(Database):
    """
    PostgreSQL database mixin.

    This mixin provides PostgreSQL-specific functionality for the Database
    class. It handles connection management, query execution, and provides
    PostgreSQL-specific features like connection pooling and transaction
    management.

    Parameters
    ----------
    connection_info : dict or None, optional
        Database connection configuration, by default None
    **kwargs
        Additional keyword arguments passed to Database

    Attributes
    ----------
    connection : psycopg2.connection or None
        PostgreSQL connection object
    cursor : psycopg2.cursor or None
        Database cursor object
    logger : Logger
        Logger instance for this database

    Notes
    -----
    Environment Variables:
        - DATABASE_DB, PG_DATABASE: Database name
        - DATABASE_USER, PG_USER: Database username
        - DATABASE_PW, PG_PASSWORD: Database password
        - DATABASE_HOST, PG_HOST: Database host
        - DATABASE_PORT, PG_PORT: Database port
        - DATABASE_SCHEMA, PG_SCHEMA: Database schema

    Examples
    --------
    Basic usage:
        >>> class MyDatabase(PostgresMixin, Database):
        ...     pass
        >>> 
        >>> with MyDatabase() as db:
        ...     results = db.query("SELECT * FROM users")

    Custom connection:
        >>> conn_info = {
        ...     'dbHost': 'localhost',
        ...     'dbPort': 5432,
        ...     'dbName': 'mydb',
        ...     'dbUser': 'user',
        ...     'dbPassword': 'pass'
        ... }
        >>> db = MyDatabase(connection_info=conn_info)
    """

    def __init__(self, connection_info: Optional[dict] = None, **kwargs):
        """
        Initialize the PostgreSQL mixin.

        Parameters
        ----------
        connection_info : dict or None, optional
            Database connection configuration, by default None
        **kwargs
            Additional keyword arguments passed to Database

        Examples
        --------
        >>> db = PostgresMixin()
        >>> db = PostgresMixin(connection_info={'dbHost': 'localhost'})
        """
        super().__init__(connection_info=connection_info, **kwargs)
        self.connection = None
        self.cursor = None
        self.logger = create_logger()

    def open(self) -> bool:
        """
        Open a connection to the PostgreSQL database.

        This method establishes a connection to the PostgreSQL database
        using the configuration provided in connection_info.

        Returns
        -------
        bool
            True if connection is successful, False otherwise

        Examples
        --------
        >>> db = PostgresMixin()
        >>> success = db.open()
        >>> print(success)
        True
        """
        try:
            self.connection = psycopg2.connect(
                host=self.connection_info["dbHost"],
                port=self.connection_info["dbPort"],
                database=self.connection_info["dbName"],
                user=self.connection_info["dbUser"],
                password=self.connection_info["dbPassword"],
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            self.logger.info("Successfully connected to PostgreSQL database")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def close(self) -> None:
        """
        Close the PostgreSQL database connection.

        This method safely closes the database connection and cursor,
        ensuring proper cleanup of resources.

        Examples
        --------
        >>> db = PostgresMixin()
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
            >>> with PostgresMixin() as db:
            ...     results = db.query("SELECT * FROM users")
            ...     print(len(results))

        Parameterized query:
            >>> with PostgresMixin() as db:
            ...     results = db.query(
            ...         "SELECT * FROM users WHERE age > %s",
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
                return self.cursor.fetchall()
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
            >>> with PostgresMixin() as db:
            ...     success = db.execute_many(
            ...         "INSERT INTO users (name, age) VALUES (%s, %s)",
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
        >>> with PostgresMixin() as db:
        ...     tables = db.get_table_names()
        ...     print(tables)
        ['users', 'orders', 'products']
        """
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """
        results = self.query(query)
        return [row['table_name'] for row in results]

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
        >>> with PostgresMixin() as db:
        ...     columns = db.get_column_info('users')
        ...     for col in columns:
        ...         print(f"{col['column_name']}: {col['data_type']}")
        id: integer
        name: character varying
        email: character varying
        """
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        return self.query(query, (table_name,))
