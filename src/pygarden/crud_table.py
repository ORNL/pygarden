#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide an abstract base class that provides basic crud operations to database tables."""

from abc import ABC

from pygarden.logz import create_logger


def convert_to_where(dictionary):
    """
    Convert a dictionary to an SQL where clause.

    :param dictionary: Key value mapping for where clause.
    :returns: A tuple containing the WHERE clause string and parameters tuple.
    :rtype: tuple
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
    Convert a dictionary to an SQL update clause.

    :param dictionary: Key value mapping for update clause.
    :returns: A tuple containing the UPDATE clause string and parameters tuple.
    :rtype: tuple
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
    """Defines a database table with standard CRUD operations"""

    def __init__(self, columns, schema, db, table_name=None):
        """
        Initialize the CRUD table.

        :param columns: Dictionary like {'id': int, 'email': str}.
        :param schema: Database schema name.
        :param db: Database connection object.
        :param table_name: Optional table name, defaults to class name in lowercase.
        """
        self.columns = columns
        self.db = db
        self.schema = schema
        self.name = table_name if table_name is not None else self.__class__.__name__.lower()
        self.logger = create_logger()

    def create(self, **kwargs):
        """
        Create an entry in the table.

        :param kwargs: Column name and value pairs for every column.
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

        :param columns: Columns to select.
        :type columns: list
        :param json: If output should be in json format.
        :type json: bool
        :param kwargs: Where clause keyword arguments.
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

        :param where: Dictionary to define the where clause.
        :type where: dict
        :param kwargs: Keys and values to update in the database.
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

        :param kwargs: Where clause keyword arguments.
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

        :param cursor: Database cursor to fetch from.
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
