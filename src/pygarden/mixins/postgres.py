#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allow opening with a psycopg2 connection."""

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn(
        "Postgres extra must be installed to use postgres \
                mixin. "
    )
    sys.exit(1)
from pygarden.env import check_environment as ce


class PostgresMixin:
    """
    Serve common connection method for postgres.

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
    DEFAULT_ENGINE = ce("DATABASE_ENGINE_PG", ce("DATABASE_ENGINE", "postgresql"))
    DEFAULT_SEARCH_PATH = ce("DATABASE_SEARCH_PATH", "public")
    DEFAULT_APPLICATION_NAME = ce("DATABASE_APPLICATION_NAME", "pygarden")

    # define a URI string if URI is perferred to connect
    DEFAULT_URI = DEFAULT_ENGINE + "://" + DEFAULT_USER + ":" + str(DEFAULT_PW) + "@" + DEFAULT_HOST + "/" + DEFAULT_DB

    def open(self, search_path=DEFAULT_SEARCH_PATH, application_name=DEFAULT_APPLICATION_NAME):
        """
        Explicitly open the database connection

        :param search_path: the search path to default to
        :return: True if connection established, else false
        """
        # Use existing connection info if provided, otherwise default to class attributes
        db_name = self.connection_info.get("dbName", PostgresMixin.DEFAULT_DB)
        db_user = self.connection_info.get("dbUser", PostgresMixin.DEFAULT_USER)
        db_password = self.connection_info.get("dbPassword", PostgresMixin.DEFAULT_PW)
        db_host = self.connection_info.get("dbHost", PostgresMixin.DEFAULT_HOST)
        db_port = self.connection_info.get("dbPort", PostgresMixin.DEFAULT_PORT)
        db_timeout = self.connection_info.get("dbTimeout", PostgresMixin.DEFAULT_TIMEOUT)

        self.logger.debug("Opening Database Connection and creating Cursor")
        self.logger.debug(self.connection_info)
        try:
            self.connection = psycopg2.connect(
                database=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                connect_timeout=db_timeout,
                application_name=application_name,
            )
            self.connection.set_client_encoding("UTF8")
            self.logger.debug("Successfully opened connection to database")
            self.cursor = self.connection.cursor()
            self.dict_cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.logger.debug("Successfully created a cursor")
            if isinstance(search_path, list):
                self.search_path = (",").join(search_path)
                # if passed as a list, split and concat into commas
            elif isinstance(search_path, str):
                self.search_path = search_path
            else:
                self.logger.error(f"Unknown type: {search_path}.")
                self.search_path = "public"
            self.cursor.execute(f"""SET search_path TO {self.search_path};""")
            self.connection.commit()
            self.logger.debug("Successfully set search_path")
        except psycopg2.OperationalError as error:
            self.logger.error(f"Database Error: {error}")
            return False
        return True

    def query(self, query, as_dict=False):
        """
        Query the database.

        :param query: A Valid SQL statement to send to the database.
        :return: None if query's cursor does not have a description, otherwise
                 return the results of using `fetchall()`

        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            self.open()  # assume that it is already open - check if it is
        self.logger.debug("Submitting user specified query to database.")
        try:
            this_cursor = self.cursor if not as_dict else self.dict_cursor
            this_cursor.execute(query)
            if this_cursor.description is not None:
                return this_cursor.fetchall()
            return None
        except psycopg2.InterfaceError as error:
            self.logger.error(f"An unexpected InterfaceError occurred: {error}")
        except psycopg2.DatabaseError as error:
            self.logger.error(f"An unexpected DatabaseError occurred: {error}")
        except psycopg2.DataError as error:
            self.logger.error(f"An unexpected DataError occurred: {error}")
        except psycopg2.IntegrityError as error:
            self.logger.error(f"An unexpected IntegrityError occurred: {error}")
        except psycopg2.ProgrammingError as error:
            self.logger.error(f"An unexpected ProgrammingError occurred: {error}")
        except psycopg2.NotSupportedError as error:
            self.logger.error(f"An unexpected NotSupportedError occurred: {error}")
        except Exception as error:
            self.logger.error("There was an undetermined issue with the query process:" + f" {error}")
        return None
