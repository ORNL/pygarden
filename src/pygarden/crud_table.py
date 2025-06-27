#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide an abstract base class that provides basic CRUD operations to database tables.

This module provides a CRUDTable class that implements Create, Read, Update, and Delete
operations for database tables. It includes utility functions for converting dictionaries
to SQL clauses and provides a comprehensive interface for database operations.

The module provides:
- CRUDTable abstract base class with full CRUD operations
- Utility functions for SQL clause generation
- Support for different column types and schemas
- JSON output formatting for query results
- Comprehensive error handling and logging

Examples
--------
Create a CRUD table class::

    >>> class Users(CRUDTable):
    ...     def __init__(self, db):
    ...         columns = {'id': int, 'name': str, 'email': str}
    ...         super().__init__(columns, 'public', db)
    >>> 
    >>> # Create a user
    >>> users.create(id=1, name='John', email='john@example.com')
    >>> 
    >>> # Read users
    >>> all_users = users.read()
    >>> specific_user = users.read(id=1)
    >>> 
    >>> # Update a user
    >>> users.update(where={'id': 1}, name='Jane')
    >>> 
    >>> # Delete a user
    >>> users.delete(id=1)

Use with specific columns::

    >>> user_names = users.read(columns=['id', 'name'])

Use with JSON output::

    >>> user_data = users.read(id=1, json=True)
"""

from abc import ABC

from pygarden.logz import create_logger


def convert_to_where(dictionary):
    """
    Convert a dictionary to an SQL WHERE clause.

    This function takes a dictionary of key-value pairs and converts them
    into a SQL WHERE clause with parameterized queries for safe execution.

    :param dictionary: Key-value mapping for WHERE clause conditions
    :type dictionary: dict
    :return: A list containing [WHERE_clause, parameters_tuple] where:
             - WHERE_clause: The formatted WHERE clause string
             - parameters_tuple: Tuple of parameter values for safe SQL execution
    :rtype: list

    Examples
    --------
    >>> convert_to_where({'id': 1, 'name': 'John'})
    ['WHERE id = %s AND name = %s', (1, 'John')]

    >>> convert_to_where({'status': 'active'})
    ['WHERE status = %s', ('active',)]

    >>> convert_to_where({})
    ['WHERE ', ()]

    Notes
    -----
    This function creates parameterized queries to prevent SQL injection.
    The returned tuple can be used directly with cursor.execute().
    """
    # result is the where clause in index 0 and the tuple for params in index 1
    result = ["WHERE ", []]
    # iterate the keys of the dictionary
    for item in dictionary.keys():
        # use the keys to build out the where clause
        result[0] += f"{item} = %s AND "
    # remove the last ' AND ' from the clause
    result[0] = result[0][:-5]
    # build the tuple for params from the dictionary's values
    result[1] = tuple(dictionary.values())
    # return the result
    return result


def convert_to_update(dictionary):
    """
    Convert a dictionary to an SQL UPDATE clause.

    This function takes a dictionary of key-value pairs and converts them
    into a SQL UPDATE clause with parameterized queries for safe execution.

    :param dictionary: Key-value mapping for UPDATE clause
    :type dictionary: dict
    :return: A list containing [UPDATE_clause, parameters_tuple] where:
             - UPDATE_clause: The formatted UPDATE clause string
             - parameters_tuple: Tuple of parameter values for safe SQL execution
    :rtype: list

    Examples
    --------
    >>> convert_to_update({'name': 'Jane', 'email': 'jane@example.com'})
    ['name = %s, email = %s', ('Jane', 'jane@example.com')]

    >>> convert_to_update({'status': 'inactive'})
    ['status = %s', ('inactive',)]

    Notes
    -----
    This function creates parameterized queries to prevent SQL injection.
    The returned tuple can be used directly with cursor.execute().
    """
    # index 0 is the update clause where index 1 is the tuple of params
    result = ["", []]
    # iterate the dictionary's keys
    for item in dictionary.keys():
        # use the keys to build out the update clause
        result[0] += f"{item} = %s, "
    # remove the last ', ' from the clause
    result[0] = result[0][:-2]
    # construct the params tuple
    result[1] = tuple(dictionary.values())
    # return the result
    return result


class CRUDTable(ABC):
    """
    Defines a database table with standard CRUD operations.

    This abstract base class provides a complete interface for Create, Read,
    Update, and Delete operations on database tables. It handles SQL generation,
    parameter binding, and database connection management.

    :param columns: Dictionary defining column names and their types (e.g., {'id': int, 'name': str})
    :type columns: dict
    :param schema: Database schema name where the table is located
    :type schema: str
    :param db: Database connection object
    :type db: Database
    :param table_name: Name of the table. If None, uses the lowercase class name
    :type table_name: str or None

    Attributes
    ----------
    columns : dict
        Column definitions for the table
    db : Database
        Database connection object
    schema : str
        Database schema name
    name : str
        Table name
    logger : Logger
        Logger instance for this table

    Examples
    --------
    Create a CRUD table for users::

        >>> class Users(CRUDTable):
        ...     def __init__(self, db):
        ...         columns = {
        ...             'id': int,
        ...             'name': str,
        ...             'email': str,
        ...             'created_at': str
        ...         }
        ...         super().__init__(columns, 'public', db)

    Create with custom table name::

        >>> class UserTable(CRUDTable):
        ...     def __init__(self, db):
        ...         columns = {'id': int, 'name': str}
        ...         super().__init__(columns, 'public', db, table_name='custom_users')

    Notes
    -----
    This class provides a complete CRUD interface and handles all database
    connection management automatically. It uses parameterized queries to
    prevent SQL injection and provides comprehensive logging.
    """

    def __init__(self, columns, schema, db, table_name=None):
        """
        Initialize the CRUD table.

        :param columns: Dictionary defining column names and their types
        :type columns: dict
        :param schema: Database schema name
        :type schema: str
        :param db: Database connection object
        :type db: Database
        :param table_name: Name of the table
        :type table_name: str or None
        """
        self.columns = columns
        self.db = db
        self.schema = schema
        self.name = table_name if table_name is not None else self.__class__.__name__.lower()
        self.logger = create_logger()

    def create(self, **kwargs):
        """
        Create an entry in the table.

        This method creates a new record in the table with the provided values.
        All columns defined in the table must be provided in the kwargs.

        :param **kwargs: Column_name=value pairs for every column in the table
        :raises AssertionError: If not all columns are provided in kwargs

        Examples
        --------
        Create a user with all required fields::

            >>> users.create(id=1, name='John', email='john@example.com', created_at='2023-01-01')

        Create with minimal fields::

            >>> users.create(id=2, name='Jane', email='jane@example.com')

        Notes
        -----
        This method automatically opens the database connection if it's not
        already open, executes the INSERT query, commits the transaction,
        and closes the connection.
        """
        # assure that all columns are defined
        # FIXME - asserts should only be used inside tests
        assert all(arg in self.columns.keys() for arg in kwargs.keys()), (
            "Must supply values for all columns to create an entry. " + f"Columns: {self.columns}"
        )
        # get a 'pretty' string of column names
        column_names = str(list(kwargs.keys()))[1:-1].replace("'", "")
        # build the query with the class's name and the kwargs that were passed
        query = (
            f"INSERT INTO {self.schema}.{self.name} "
            f"({column_names}) "
            f"VALUES ({', '.join(['%s']*len(kwargs.keys()))})"
        )
        # tell the user that we are executing an insert query
        self.logger.info(f"Executing query: {query} " + f"params: {tuple(kwargs.values())}")
        try:
            # if the db is not open..
            if not self.db.is_open():
                # open the database connection
                self.db.open()
            # get the cursor from the database
            curr = self.db.cursor
            # execute the query we built
            curr.execute(query, tuple(kwargs.values()))
            # commit the changes to the database
            self.db.connection.commit()
        except Exception as err:
            # close the connection to the database
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

        This method retrieves records from the table based on the provided
        conditions. It supports selecting specific columns, filtering with
        WHERE clauses, and returning results in JSON format.

        :param columns: Columns to select. If None, selects all columns (*)
        :type columns: list or str or None
        :param json: If True, returns results in JSON format
        :type json: bool
        :param **kwargs: WHERE clause conditions as keyword arguments
        :return: Query results. Returns None if query fails
        :rtype: list or dict or None
        :raises AssertionError: If specified columns are not found in the table definition
        :raises TypeError: If columns parameter is not a list or string

        Examples
        --------
        Read all records::

            >>> all_users = users.read()

        Read specific columns::

            >>> user_names = users.read(columns=['id', 'name'])

        Read with WHERE clause::

            >>> user = users.read(id=1)

        Read in JSON format::

            >>> user_json = users.read(id=1, json=True)

        Read with multiple conditions::

            >>> active_users = users.read(status='active', role='user')

        Notes
        -----
        This method automatically opens the database connection if it's not
        already open, executes the SELECT query, fetches the results,
        and closes the connection.
        """
        # define the select clause (this will remain the same unless we are
        # selecting specific columns
        select_clause = "*"
        # define the where clause (again this will change the same unless some
        # kwargs are defined
        where_clause = None
        # initialize the query
        query = None
        # initialize the data to return
        data = None
        # if the caller specified any kwargs (we know that we are going to
        # have a where clause)
        if len(kwargs) > 0:
            # assure that every column specified in kwargs are define in
            # self.columns
            assert all(column in self.columns for column in kwargs), (
                "Column(s) specified in kwargs could not be found. " + "Please check kwargs definition and try again."
            )
            # construct and assign the where clause with the
            # conversion function
            where_clause = convert_to_where(kwargs)
        # if the caller specified some columns to select...
        if columns is not None:
            # check if columns is a list
            if isinstance(columns, list):
                # assure that every specfied column in columns are defined in
                # self.columns
                assert all(column in self.columns for column in columns), (
                    "Column(s) specified in columns could not be found. "
                    + "Please check columns definition and try again."
                )
                # construct a 'select' clause from the list
                select_clause = str(columns)[1:-1].replace("'", "")
            # is columns is a string...
            elif isinstance(columns, str):
                # assure that the column specified is defined in self.columns
                assert columns in self.columns, (
                    "Could not find column " + f"{columns} in self.columns definition: {self.columns}"
                )
                # use the column specified as the select clause
                select_clause = columns
            # if columns is of any other type...
            else:
                # raise an exception as we do not know what to do
                raise TypeError("column argument should be of type list or" + f" str not {type(columns)}")
        # if the where clause was not set/specified
        if where_clause is None:
            try:
                # make a query to select the columns with no where clause
                query = f"SELECT {select_clause} " + f"FROM {self.schema}.{self.name}"
                # inform the user we are executing the query..
                self.logger.info(f"Executing query: {query}")
                # if the db is not already opened..
                if not self.db.is_open():
                    # open the connection to the database
                    self.db.open()
                # get the cursor from the database
                curr = self.db.cursor
                # execute the query
                curr.execute(query)
            except Exception as err:
                self.logger.error("Exception occured when trying to execute " + f"query: {query}")
                self.logger.error(f"Exception Message: {err}")

        # if there is a where clause...
        else:
            try:
                # make a query to select the columns with the where clause
                query = f"SELECT {select_clause} " + f"FROM {self.schema}.{self.name} " + f"{where_clause[0]}"
                # tell the user we are executing their query
                self.logger.info(f"Executing query: {query} " + f"params: {where_clause[1]}")
                # if the db is not already opened..
                if not self.db.is_open():
                    # open the connection to the database
                    self.db.open()
                # get the cursor from the database
                curr = self.db.cursor
                # execute the query with the where clause params
                curr.execute(query, where_clause[1])
            except Exception as err:
                self.logger.error(
                    "Exception occured when trying to execute "
                    + f"query: {query} with "
                    + f"parameters: {where_clause[1]}"
                )
                self.logger.error(f"Exception Message: {err}")
                # close the connection to the database
                self.db.close()
        try:
            # if the user wants json output..
            if json is not None and json:
                # use the fetch_json method to get json output from the
                # database
                data = self.fetch_json(curr)
            # if the user doesn't want json..
            else:
                # simply fetch the results from the db
                data = curr.fetchall()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to fetch "
                + f"results from query: {query} with "
                + f"parameters: {where_clause[1]}"
            )
            self.logger.error(f"Exception Message: {err}")
            # return the results from the database
        finally:
            # close the connection to the database
            self.db.close()
            # return the data (will be none if query failed)
        return data

    def update(self, where: dict, **kwargs):
        """
        Update entries in the table.

        This method updates records in the table based on the provided WHERE
        conditions. It requires both a WHERE clause and update values.

        :param where: Dictionary defining the WHERE clause conditions
        :type where: dict
        :param **kwargs: Column_name=value pairs to update
        :raises AssertionError: If no WHERE clause or no update fields are provided

        Examples
        --------
        Update a user's name::

            >>> users.update(where={'id': 1}, name='Jane')

        Update multiple fields::

            >>> users.update(where={'email': 'old@example.com'}, name='John', email='new@example.com')

        Update with multiple conditions::

            >>> users.update(where={'status': 'active', 'role': 'user'}, last_login='2023-01-01')

        Notes
        -----
        This method automatically opens the database connection if it's not
        already open, executes the UPDATE query, commits the transaction,
        and closes the connection.
        """
        # ensure there is a where clause
        assert where is not None and len(where) > 0, "No where clause found." + "\nUpdate must have a where clause!"
        # ensure that some update was specified in the kwargs
        assert kwargs is not None and len(kwargs) > 0, (
            "No keyword arguments supplied." + "\nUpdate must have a field to update!"
        )

        try:
            # construct the where clause with the conversion method
            where_clause = convert_to_where(where)
            # construct the update clause with the conversion method
            update_clause = convert_to_update(kwargs)
            # construct the parms for the update statement
            params = (*update_clause[1], *where_clause[1])
            # build a query to update the specified values in the db
            query = f"UPDATE {self.schema}.{self.name} " + f"SET {update_clause[0]} " + f"{where_clause[0]}"
            # tell the user we are executing their query
            self.logger.info(f"Executing query: {query} params: {params}")
            # if the db is not open..
            if not self.db.is_open():
                # open a connection to the db
                self.db.open()
            # get the cursor from the db
            curr = self.db.cursor
            # execute the query we constructed
            curr.execute(query, params)
            # commit the changes to the database
            self.db.connection.commit()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to execute " + f"query: {query} with " + f"parameters: {params}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            # close the connection to the database
            self.db.close()

    def delete(self, **kwargs):
        """
        Delete entries from the table.

        This method deletes records from the table based on the provided
        WHERE conditions. It requires at least one condition to prevent
        accidental deletion of all records.

        :param **kwargs: WHERE clause conditions as keyword arguments
        :raises AssertionError: If no WHERE clause is provided

        Examples
        --------
        Delete a user by ID::

            >>> users.delete(id=1)

        Delete users by email::

            >>> users.delete(email='old@example.com')

        Delete with multiple conditions::

            >>> users.delete(status='inactive', last_login='2022-01-01')

        Notes
        -----
        This method automatically opens the database connection if it's not
        already open, executes the DELETE query, commits the transaction,
        and closes the connection.
        """
        # ensure that some kwargs were passed
        assert kwargs is not None and len(kwargs) > 0, (
            "No keyword arguments supplied." + "\nDelete must have a where clause!"
        )
        try:
            # construct the where clause with the conversion method
            where_clause = convert_to_where(kwargs)
            # build a delete query with the specified values
            query = f"DELETE FROM {self.schema}.{self.name} " + f"{where_clause[0]}"
            # tell the user that we are executing their query
            self.logger.info(f"Executing query: {query}, " + f"params: {where_clause[1]}")
            # if the db is not open..
            if not self.db.is_open():
                # open a connection to the database
                self.db.open()
            # get the cursor from the database
            curr = self.db.cursor
            # execute the query
            curr.execute(query, where_clause[1])
            # commit the changes to the database
            self.db.connection.commit()
        except Exception as err:
            self.logger.error(
                "Exception occured when trying to execute " + f"query: {query} with " + f"parameters: {where_clause[1]}"
            )
            self.logger.error(f"Exception Message: {err}")
        finally:
            # close the connection
            self.db.close()

    def fetch_json(self, cursor):
        """
        Fetch JSON/dictionary data from the database.

        This method converts database query results into a JSON-like
        dictionary format with row numbers as keys and column data as
        nested dictionaries.

        :param cursor: Database cursor to fetch from
        :type cursor: cursor
        :return: Dictionary with row data indexed by row number
        :rtype: dict

        Examples
        --------
        >>> results = users.read(json=True)
        >>> print(results)
        {'0': {'id': '1', 'name': 'John', 'email': 'john@example.com'}}

        >>> results = users.read(columns=['name'], json=True)
        >>> print(results)
        {'0': {'name': 'John'}, '1': {'name': 'Jane'}}

        Notes
        -----
        This method converts all values to strings for JSON compatibility.
        Row numbers start from 0 and are used as dictionary keys.
        """
        # initialize local vars
        columns = {}
        result = {}
        index = 0

        # iterate the cursor's description to get the column names in question
        for d in cursor.description:
            columns[str(index)] = d[0]
            index = index + 1

        # restart the index back to 0
        index = 0
        # iterate the result of the query
        for row in cursor.fetchall():
            # init a place for the json object for this row to exist
            result[str(index)] = {}
            # iterate the length of the result
            for i in range(0, len(row)):
                # assign the json object to the result from the database
                result[str(index)][columns[str(i)]] = str(row[i])

        # return the result
        return result
