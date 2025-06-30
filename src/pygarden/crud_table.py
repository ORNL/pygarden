#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide an abstract base class that provides basic CRUD operations to database tables.

This module defines the CRUDTable abstract base class, which provides standard
Create, Read, Update, and Delete operations for database tables, as well as
helper functions for SQL clause construction. It is designed to be subclassed
for specific table implementations.
"""

from abc import ABC
from pygarden.logz import create_logger


def convert_to_where(dictionary):
    """
    Convert a dictionary to an SQL WHERE clause and parameter tuple.

    :param dictionary: Key-value mapping for the WHERE clause (e.g., {'id': 1, 'name': 'foo'}).
    :type dictionary: dict
    :return: A list where index 0 is the WHERE clause string (e.g., 'WHERE id = %s AND name = %s')
             and index 1 is a tuple of parameter values (e.g., (1, 'foo')).
    :rtype: list
    :raises ValueError: If the dictionary is empty.
    :example:
        >>> convert_to_where({'id': 1, 'name': 'foo'})
        ['WHERE id = %s AND name = %s', (1, 'foo')]
    """
    if not dictionary:
        raise ValueError("Dictionary for WHERE clause cannot be empty.")
    result = ["WHERE ", []]
    for item in dictionary.keys():
        result[0] += f"{item} = %s AND "
    result[0] = result[0][:-5]
    result[1] = tuple(dictionary.values())
    return result


def convert_to_update(dictionary):
    """
    Convert a dictionary to an SQL UPDATE clause and parameter tuple.

    :param dictionary: Key-value mapping for the UPDATE clause (e.g., {'name': 'foo'}).
    :type dictionary: dict
    :return: A list where index 0 is the UPDATE clause string (e.g., 'name = %s')
             and index 1 is a tuple of parameter values (e.g., ('foo',)).
    :rtype: list
    :raises ValueError: If the dictionary is empty.
    :example:
        >>> convert_to_update({'name': 'foo'})
        ['name = %s', ('foo',)]
    """
    if not dictionary:
        raise ValueError("Dictionary for UPDATE clause cannot be empty.")
    result = ["", []]
    for item in dictionary.keys():
        result[0] += f"{item} = %s, "
    result[0] = result[0][:-2]
    result[1] = tuple(dictionary.values())
    return result


class CRUDTable(ABC):
    """
    Abstract base class for a database table with standard CRUD operations.

    This class provides methods for creating, reading, updating, and deleting
    entries in a database table. It is intended to be subclassed for specific
    table implementations.

    **Attributes:**
        columns (dict): Mapping of column names to types (e.g., {'id': int, 'email': str}).
        db: Database connection object (must implement .is_open(), .open(), .close(), .cursor, .connection).
        schema (str): Database schema name.
        name (str): Table name (defaults to lowercase class name if not provided).
        logger: Logger instance for query logging.

    **Usage Notes:**
        - All CRUD operations are logged.
        - All methods close the database connection after execution.
        - Asserts are used for argument validation; consider replacing with exceptions in production.
        - Subclasses may override methods for custom behavior.
    """

    def __init__(self, columns, schema, db, table_name=None):
        """
        Initialize the CRUDTable instance.

        :param columns: Dictionary mapping column names to types.
        :type columns: dict
        :param schema: Database schema name.
        :type schema: str
        :param db: Database connection object.
        :type db: object
        :param table_name: Optional table name (defaults to lowercase class name).
        :type table_name: str, optional
        """
        self.columns = columns
        self.db = db
        self.schema = schema
        self.name = table_name if table_name is not None else self.__class__.__name__.lower()
        self.logger = create_logger()

    def create(self, **kwargs):
        """
        Insert a new entry into the table.

        :param kwargs: Column name-value pairs for every column to insert.
        :raises AssertionError: If any provided column is not in self.columns.
        :return: None
        :side effects: Commits the transaction and closes the database connection.
        :example:
            >>> table.create(id=1, email='foo@bar.com')
        """
        assert all(arg in self.columns.keys() for arg in kwargs.keys()), (
            "Must supply values for all columns to create an entry. " + f"Columns: {self.columns}"
        )
        column_names = str(list(kwargs.keys()))[1:-1].replace("'", "")
        query = (
            f"INSERT INTO {self.schema}.{self.name} "
            f"({column_names}) "
            f"VALUES ({', '.join(['%s']*len(kwargs.keys()))})"
        )
        self.logger.info(f"Executing query: {query} " + f"params: {tuple(kwargs.values())}")
        try:
            if not self.db.is_open():
                self.db.open()
            curr = self.db.cursor
            curr.execute(query, tuple(kwargs.values()))
            self.db.connection.commit()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to execute "
                + f"query: {query} with "
                + f"parameters: {tuple(kwargs.values())}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            self.db.close()

    def read(self, columns: list = None, json: bool = False, **kwargs):
        """
        Read entries from the table.

        :param columns: Columns to select (list or str). If None, selects all columns.
        :type columns: list or str, optional
        :param json: If True, returns output in JSON format; otherwise, returns list of tuples.
        :type json: bool, optional
        :param kwargs: Where clause keyword arguments (e.g., id=1).
        :raises AssertionError: If specified columns or where keys are not in self.columns.
        :raises TypeError: If columns is not a list or string.
        :return: Query results as list of tuples or JSON/dict if json=True.
        :side effects: Closes the database connection after execution.
        :example:
            >>> table.read(columns=['id', 'email'], id=1)
            [(1, 'foo@bar.com')]
        """
        select_clause = "*"
        where_clause = None
        query = None
        data = None
        if len(kwargs) > 0:
            assert all(column in self.columns for column in kwargs), (
                "Column(s) specified in kwargs could not be found. " + "Please check kwargs definition and try again."
            )
            where_clause = convert_to_where(kwargs)
        if columns is not None:
            if isinstance(columns, list):
                assert all(column in self.columns for column in columns), (
                    "Column(s) specified in columns could not be found. "
                    + "Please check columns definition and try again."
                )
                select_clause = str(columns)[1:-1].replace("'", "")
            elif isinstance(columns, str):
                assert columns in self.columns, (
                    "Could not find column " + f"{columns} in self.columns definition: {self.columns}"
                )
                select_clause = columns
            else:
                raise TypeError("column argument should be of type list or" + f" str not {type(columns)}")
        if where_clause is None:
            try:
                query = f"SELECT {select_clause} " + f"FROM {self.schema}.{self.name}"
                self.logger.info(f"Executing query: {query}")
                if not self.db.is_open():
                    self.db.open()
                curr = self.db.cursor
                curr.execute(query)
            except Exception as err:
                self.logger.error("Exception occured when trying to execute " + f"query: {query}")
                self.logger.error(f"Exception Message: {err}")
        else:
            try:
                query = f"SELECT {select_clause} " + f"FROM {self.schema}.{self.name} " + f"{where_clause[0]}"
                self.logger.info(f"Executing query: {query} " + f"params: {where_clause[1]}")
                if not self.db.is_open():
                    self.db.open()
                curr = self.db.cursor
                curr.execute(query, where_clause[1])
            except Exception as err:
                self.logger.error(
                    "Exception occured when trying to execute "
                    + f"query: {query} with "
                    + f"parameters: {where_clause[1]}"
                )
                self.logger.error(f"Exception Message: {err}")
                self.db.close()
        try:
            if json is not None and json:
                data = self.fetch_json(curr)
            else:
                data = curr.fetchall()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to fetch "
                + f"results from query: {query} with "
                + f"parameters: {where_clause[1]}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            self.db.close()
        return data

    def update(self, where: dict, **kwargs):
        """
        Update entries in the table matching the WHERE clause.

        :param where: Dictionary to define the WHERE clause (e.g., {'id': 1}).
        :type where: dict
        :param kwargs: Keys and values to update in the database (e.g., name='foo').
        :raises AssertionError: If no where clause or update fields are provided.
        :return: None
        :side effects: Commits the transaction and closes the database connection.
        :example:
            >>> table.update(where={'id': 1}, name='bar')
        """
        assert where is not None and len(where) > 0, "No where clause found.\nUpdate must have a where clause!"
        assert kwargs is not None and len(kwargs) > 0, (
            "No keyword arguments supplied.\nUpdate must have a field to update!"
        )
        try:
            where_clause = convert_to_where(where)
            update_clause = convert_to_update(kwargs)
            params = (*update_clause[1], *where_clause[1])
            query = f"UPDATE {self.schema}.{self.name} " + f"SET {update_clause[0]} " + f"{where_clause[0]}"
            self.logger.info(f"Executing query: {query} params: {params}")
            if not self.db.is_open():
                self.db.open()
            curr = self.db.cursor
            curr.execute(query, params)
            self.db.connection.commit()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to execute " + f"query: {query} with " + f"parameters: {params}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            self.db.close()

    def delete(self, **kwargs):
        """
        Delete entries from the table matching the WHERE clause.

        :param kwargs: Where clause to delete on (e.g., id=1).
        :raises AssertionError: If no where clause is provided.
        :return: None
        :side effects: Commits the transaction and closes the database connection.
        :example:
            >>> table.delete(id=1)
        """
        assert kwargs is not None and len(kwargs) > 0, (
            "No keyword arguments supplied.\nDelete must have a where clause!"
        )
        try:
            where_clause = convert_to_where(kwargs)
            query = f"DELETE FROM {self.schema}.{self.name} " + f"{where_clause[0]}"
            self.logger.info(f"Executing query: {query}, " + f"params: {where_clause[1]}")
            if not self.db.is_open():
                self.db.open()
            curr = self.db.cursor
            curr.execute(query, where_clause[1])
            self.db.connection.commit()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to execute " + f"query: {query} with " + f"parameters: {where_clause[1]}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            self.db.close()

    def fetch_json(self, cursor):
        """
        Fetch query results from the database cursor as a JSON/dict object.

        :param cursor: Database cursor to fetch from (must have .description and .fetchall()).
        :type cursor: object
        :return: Dictionary containing the query results in JSON format, where each key is a row index as a string.
        :rtype: dict
        :example:
            >>> table.fetch_json(cursor)
            {'0': {'id': '1', 'name': 'foo'}, '1': {'id': '2', 'name': 'bar'}}
        """
        columns = {}
        result = {}
        index = 0
        for d in cursor.description:
            columns[str(index)] = d[0]
            index = index + 1
        index = 0
        for row in cursor.fetchall():
            result[str(index)] = {}
            for i in range(0, len(row)):
                result[str(index)][columns[str(i)]] = str(row[i])
        return result
