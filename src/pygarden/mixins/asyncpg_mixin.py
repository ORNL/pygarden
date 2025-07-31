#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allow opening with an asyncpg connection."""

try:
    import asyncpg
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn("asyncpg extra must be installed to use asyncpg mixin. " "Install with: pip install asyncpg")
    sys.exit(1)

from pygarden.env import check_environment as ce


class AsyncPostgresMixin:
    """
    Serve common async connection method for postgres using asyncpg.

    The default `search_path` variable can be set with the following
    operating system variable:
        - DATABASE_SEARCH_PATH
    """

    DEFAULT_DB = ce("DATABASE_DB_PG", ce("DATABASE_DB", ce("PG_DATABASE", "postgres")))
    DEFAULT_USER = ce("DATABASE_USER_PG", ce("DATABASE_USER", ce("PG_USER", "postgres")))
    DEFAULT_PW = ce("DATABASE_PW_PG", ce("DATABASE_PW", ce("PG_PASSWORD", "postgres")))
    DEFAULT_HOST = ce("DATABASE_HOST_PG", ce("DATABASE_HOST", ce("PG_HOST", "localhost")))
    DEFAULT_PORT = int(ce("DATABASE_PORT_PG", ce("DATABASE_PORT", ce("PG_PORT", 5432))))
    DEFAULT_TIMEOUT = ce("DATABASE_TIMEOUT", ce("PG_TIMEOUT", 60))
    DEFAULT_SCHEMA = ce("DATABASE_SCHEMA_PG", ce("DATABASE_SCHEMA", ce("PG_SCHEMA", "public")))
    DEFAULT_ENGINE = ce("DATABASE_ENGINE_PG", ce("DATABASE_ENGINE", "postgresql+asyncpg"))
    DEFAULT_SEARCH_PATH = ce("DATABASE_SEARCH_PATH", "public")
    DEFAULT_APPLICATION_NAME = ce("DATABASE_APPLICATION_NAME", "pygarden")
    DEFAULT_PREFETCH_AMOUNT = ce("DEFAULT_PREFETCH_AMOUNT", "500")

    # define a URI string if URI is preferred to connect
    DEFAULT_URI = DEFAULT_ENGINE + "://" + DEFAULT_USER + ":" + str(DEFAULT_PW) + "@" + DEFAULT_HOST + "/" + DEFAULT_DB

    def __del__(self):
        """Deletion is handled automatically"""

    async def open(self, search_path=DEFAULT_SEARCH_PATH, application_name=DEFAULT_APPLICATION_NAME):
        """
        Explicitly open the async database connection

        :param search_path: the search path to default to
        :param application_name: the application name for the connection
        :return: True if connection established, else false
        """
        # Use existing connection info if provided, otherwise default to class attributes
        db_name = self.connection_info.get("dbName", AsyncPostgresMixin.DEFAULT_DB)
        db_user = self.connection_info.get("dbUser", AsyncPostgresMixin.DEFAULT_USER)
        db_password = self.connection_info.get("dbPassword", AsyncPostgresMixin.DEFAULT_PW)
        db_host = self.connection_info.get("dbHost", AsyncPostgresMixin.DEFAULT_HOST)
        db_port = self.connection_info.get("dbPort", AsyncPostgresMixin.DEFAULT_PORT)
        db_timeout = self.connection_info.get("dbTimeout", AsyncPostgresMixin.DEFAULT_TIMEOUT)

        self.logger.debug("Opening Async Database Connection")
        self.logger.debug(self.connection_info)
        try:
            self.connection = await asyncpg.connect(
                database=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                command_timeout=db_timeout,
                server_settings={"application_name": application_name},
            )
            self.logger.debug("Successfully opened async connection to database")

            # Set search path
            if isinstance(search_path, list):
                self.search_path = ",".join(search_path)
            elif isinstance(search_path, str):
                self.search_path = search_path
            else:
                self.logger.error(f"Unknown type: {search_path}.")
                self.search_path = self.DEFAULT_SEARCH_PATH

            await self.connection.execute(f"""SET search_path TO {self.search_path};""")
            self.logger.debug("Successfully set search_path")
        except asyncpg.PostgresError as error:
            self.logger.error(f"Database Error: {error}")
            return False
        return True

    async def query(self, query, *args, as_dict=False):
        """
        Query the database asynchronously.

        :param query: A Valid SQL statement to send to the database.
        :param args: Parameters for the query (for parameterized queries)
        :param as_dict: If True, return results as dictionaries
        :return: None if query doesn't return results, otherwise return the results
        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            await self.open()

        self.logger.debug("Submitting user specified query to database.")
        try:
            results = []
            data = False
            async with self.connection.transaction():
                async for row in self.connection.cursor(query, *args, prefetch=int(AsyncPostgresMixin.DEFAULT_PREFETCH_AMOUNT)):
                    data = True
                    results.append(row)
            if not data:
                return None
            return [dict(row) for row in results] if as_dict else results
        except asyncpg.PostgresError as error:
            self.logger.error(f"Database error occurred: {error}")
        except Exception as error:
            self.logger.error("There was an undetermined issue with the query process: " + f" {error}")
        return None

    async def execute(self, query, *args):
        """
        Execute a query that doesn't return results (INSERT, UPDATE, DELETE, etc.)

        :param query: A Valid SQL statement to send to the database.
        :param args: Parameters for the query
        :return: The result of the execution
        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            await self.open()

        self.logger.debug("Executing query on database.")
        try:
            result = await self.connection.execute(query, *args)
            return result
        except asyncpg.PostgresError as error:
            self.logger.error(f"Database error occurred: {error}")
        except Exception as error:
            self.logger.error("There was an undetermined issue with the query process: " + f" {error}")
        return None

    async def fetch(self, query, *args):
        """
        Fetch multiple rows from the database.

        :param query: A SELECT query to execute
        :param args: Parameters for the query
        :return: List of rows
        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            await self.open()

        self.logger.debug("Fetching rows from database.")
        try:
            results = await self.connection.fetch(query, *args)
            return results
        except asyncpg.PostgresError as error:
            self.logger.error(f"Database error occurred: {error}")
        except Exception as error:
            self.logger.error("There was an undetermined issue with the fetch process: " + f" {error}")
        return None

    async def fetchval(self, query, *args):
        """
        Fetch a single value from the database.

        :param query: A SELECT query that returns a single value
        :param args: Parameters for the query
        :return: The single value
        """
        rows = await self.query(query, *args)
        return next(iter(rows))[0] if len(rows) > 0 else None

    async def fetchrow(self, query, *args):
        """
        Fetch a single row from the database.

        :param query: A SELECT query that returns a single row
        :param args: Parameters for the query
        :return: The single row
        """
        rows = await self.query(query, *args)
        return next(iter(rows)) if len(rows) > 0 else None

    async def close(self):
        """
        Close the database connection.

        :return: None
        """
        if self.is_open():
            await self.connection.close()
            self.logger.debug("Successfully closed database connection")

    def is_open(self):
        """
        Check if the database connection is open.

        :return: True if connection is open, False otherwise
        """
        return hasattr(self, "connection") and self.connection and not self.connection.is_closed()

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
