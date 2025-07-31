#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allow opening with a pymssql connection."""

import traceback

try:
    import pymssql
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn("PyMSSQL extra must be installed to use mixin. ")
    sys.exit(1)

from pygarden.env import check_multi_environment as cme


class MSSQLMixin:
    """
    Provides a convenient API-like interface to Microsoft SQL databases.

    The database object is the interface to the database.
    """

    DEFAULT_DB = cme("DATABASE_DB_MS", "CommonDB", "DATABASE_DB", "postgres")
    DEFAULT_USER = cme("DATABASE_USER_MS", "sa", "DATABASE_USER", "postgres")
    DEFAULT_PW = cme("DATABASE_PW_MS", "5nowDog5", "DATABASE_PW", "postgres")
    DEFAULT_HOST = cme("DATABASE_HOST_MS", "mssql", "DATABASE_HOST", "localhost")
    DEFAULT_PORT = int(cme("DATABASE_PORT_MS", 1433, "DATABASE_PORT"))

    def __del__(self):
        """
        Close the connection to database.

        Ensure function call is superior to Database i.e:
        class MSSQLDB(MSSQLMixin, Database):
        """
        self.close()

    def open(self):
        """
        Open the connection to the database.

        :return: True if connection established, else false
        """
        self.logger.debug("Opening Database Object")

        db_name = self.connection_info.get("dbName", MSSQLMixin.DEFAULT_DB)
        db_user = self.connection_info.get("dbUser", MSSQLMixin.DEFAULT_USER)
        db_password = self.connection_info.get("dbPassword", MSSQLMixin.DEFAULT_PW)
        db_host = self.connection_info.get("dbHost", MSSQLMixin.DEFAULT_HOST)

        try:
            msg = "\nConnecting information\n" + f"Database: {db_name}\n" + f"Host: {db_host}\n" + f"User: {db_user}\n"
            self.logger.debug(msg)
            self.connection = pymssql.connect(
                database=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
            )
            self.logger.debug("Successfully opened database connection")
            self.cursor = self.connection.cursor()
            self.logger.debug("Successfully created database cursor")
            return True
        except pymssql.OperationalError as e:
            self.logger.error(f"Database error: {e}")
            return False

    def close(self):
        """Close the database connection. No logging."""
        if hasattr(self, "cursor") and self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if hasattr(self, "connnection") and self.connection is not None:
            self.connection.commit()
            self.connection.close()
            self.connection = None
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.dispose()

    def query(self, query):
        """Send a query to the database and retrieve the results."""
        self.logger.debug(f"Initiating query: {query}")
        try:
            self.cursor.execute(query)
            res = self.cursor.fetchall()
        except Exception as e:
            traceback.print_stack()
            self.logger.error(f"Problem querying database: {e}")
            res = None
        return res
