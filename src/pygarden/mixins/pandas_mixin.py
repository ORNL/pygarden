#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a `pandas` mixin for the Database class."""

try:
    import pandas as pd
    import sqlalchemy
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn("db-pandas extra must be installed to use mixin. ")
    sys.exit(1)


class PandasMixin:
    """
    Group together all pandas logic.

    This mixin provides pandas DataFrame functionality for database operations.
    """

    def query_pandas(self, query=None, table=None, schema=None, log_df=False, log_query=False):
        """
        Return a query as a pandas table.

        Provided a query, uses the default cursor assuming a
        PostgreSQL connection.

        :param query: A query string to return as a table.
        :param table: The table name to retrieve data from.
        :param schema: The schema to select the table from.
        :param log_df: Should the dataframe be logged? (default: False).
        :param log_query: Should the query be logged? (default: False).
        :return: A pandas.DataFrame object.
        """

        def make_dataframe(query):
            """
            Create a pandas dataframe from a query.

            :param query: The SQL query to execute.
            :return: A pandas DataFrame containing the query results.
            """
            if self.cursor is None:
                # TODO raise an appropriate error here
                self.logger.error("Cursor is not open, please create one.")
            # TODO wrap in a try except block
            self.logger.debug(f"Returning {query} as pandas dataframe.")

            self.cursor.execute(query)
            # https://www.psycopg.org/docs/cursor.html
            # Comments on the execute method:
            #   The method returns None. If a query was executed,
            #   the returned values can be retrieved using fetch*() methods.
            result = self.cursor.fetchall()
            if result is None:
                self.logger.error("Query returned: 'None' for query " f"'{query}'")
            else:
                if log_query:
                    self.logger.debug(f"Query returned: '{result}' for query " f"'{query}'")

            columns = [i[0] for i in self.cursor.description]

            dataframe = pd.DataFrame.from_records(result, columns=columns)
            # dataframe.columns = result.keys()
            if log_df:
                self.logger.info(f"Fetched Dataframe: {dataframe}")
            return dataframe

        if query is not None and not isinstance(self.connection, sqlalchemy.engine.base.Engine):
            return make_dataframe(query)
        if table is not None and schema is not None and isinstance(self.connection, sqlalchemy.engine.base.Engine):
            return pd.read_from_table(table_name=table, schema=schema)
        if query is not None and isinstance(self.connection, sqlalchemy.engine.base.Engine):
            return pd.read_sql_from_query(query, ur=self.connection_inf["uri"])
