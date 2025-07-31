#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abstract Database class for connecting to a database.

This class provides an abstract method of interacting with a (by default)
PostgreSQL database. However, the connection paramater may be specified to open
any type of connection through implementation of this abstract class.
"""

import traceback
from abc import ABC
from typing import Optional

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class Database(ABC):
    """
    Provides an abstract class for connecting to a database using environmental variables.

    Connection info stored in system environment variables:
        - DATABASE_TIMEOUT, PG_TIMEOUT: an integer representing the seconds to wait
                            before deciding a timeout occurred.
        - DATABASE_DB, PG_DATABASE: a string representing the database to connect to
        - DATABASE_USER, PG_USER: a string representing the user to connect to the
                         database as
        - DATABASE_PW, PG_PASSWORD: a string representing the password for the
                       DATABASE_USER
        - DATABASE_HOST, PG_HOST: a string representing the hostname or IP address
                         hosting the database
        - DATABASE_PORT, PG_PORT: an integer representing the port to connect to the
                         database on
        - DATABASE_SCHEMA, PG_SCHEMA: a string representing the schema to default to
                           when creating a database connection

    Log file info stored in system environment variables:
        - DATABASE_LOG_PATH: a string representing the file path to record
                            all logged data. defaults to, ""
        - DATABASE_LOG_MODE: a string representing the mode to open the log
                             file. Standard convention for file modes are
                             used. defaults to, "a"
        - DATABASE_LOG_ENCODING: a string representing the type of encoding
                                 to use when handling the log file.
                                 defaults to, "utf-8"

    :param connection_info: a dictionary containing connection information
    derived from the environmental variables described above.

    :note: It is best practice to use `with` to enter the database rather
    than explicitly calling the `open` function, as database connection
    will be created and destroyed behind the scenes, preventing lingering
    database connections.

    :note: File logging is disabled by default.
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
    # define a URI string if URI is perferred to connect
    DEFAULT_URI = f"{DEFAULT_ENGINE}://{DEFAULT_USER}:{str(DEFAULT_PW)}" + f"@{DEFAULT_HOST}/{DEFAULT_DB}"

    def __init__(
        self,
        log_file_info: Optional[dict] = None,
        connection_info: Optional[dict] = None,
        **kwargs,
    ):
        """
        Create a Database object.

        This *does not* open a connection to the database.  Use open() or `with` to establish a database connection.

        :param log_file_info: A dictionary containing log file info.
        :param connection_info: A dictionary containing connection info.
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
        Make any pending database commits and close the connection.

        Note that you *should not* rely on this to close connection; you
        should explicitly use close() to sever database connections.  That
        is, the python garbage collector is *not guaranteed to run* when
        execution scope would sever the last reference to a Database
        object, nor even when the script finishes execution.
        """
        self.logger.debug("Deleting Database Object")
        self.close()

    def __enter__(self):
        """Allow database to be entered via with."""
        self.silent_open()
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """Handle database closing when leaving with."""
        self.close()

    def silent_open(self):
        """Open database silently without returning anything."""
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
        Explicitly close the connection.

        :returns: None
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.connection:
            self.connection.commit()
            self.connection.close()
            self.connection = None

    def is_open(self):
        """Determine if the database is open or not.

        :returns: True if database is open, False otherwise.
        :rtype: bool
        """
        if self.cursor is not None and self.connection is not None:
            return True  # If both are on, return True
        # If one or both connection and cursor are missing, return False
        return False

    def override_connection(self, connection):
        """
        Override the default connection.

        This is useful for using other connections than `psycopg2` for downstream development.

        :param connection: Any type of database connection object.
        """
        self.connection = connection

    def modify_connection_info(self, variable, value):
        """
        Modify a `variable` and set it to `value` in the connection_info attribute.

        :param variable: The connection variable to set.
        :param value: The value for the connection variable.
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
        **kwargs,
    ):
        """
        Creates the complete connection_info dictionary to use for database connection.

        This method generates a dictionary containing all the necessary information for
        establishing a connection to a database. It constructs the connection URI based
        on the provided parameters and defaults to certain values if parameters are not
        provided.

        :param db_name: The name of the database. Defaults to Database.DEFAULT_DB.
        :param db_user: The database user. Defaults to Database.DEFAULT_USER.
        :param db_password: The password for the database user. Defaults to Database.DEFAULT_PW.
        :param db_host: The host where the database is located. Defaults to Database.DEFAULT_HOST.
        :param db_port: The port on which the database is listening. Defaults to Database.DEFAULT_PORT.
        :param db_schema: The schema to use within the database. Defaults to Database.DEFAULT_SCHEMA.
        :param db_type: The type of the database (e.g., 'postgres', 'mssql'). Used to infer db_engine.
        :param db_engine: The SQLAlchemy database engine string (e.g., 'postgresql', 'mssql+pymssql').
                          If not provided, it is inferred from db_type or defaults to Database.DEFAULT_ENGINE.
        :param db_timeout: The timeout setting for the database connection. Defaults to Database.DEFAULT_TIMEOUT.
        :param kwargs: Additional keyword arguments that may be used.
        :returns: A dictionary containing connection information.
        :rtype: dict
        """
        if db_type and not db_engine:
            if db_type.startswith("postgres") or db_type.startswith("pg"):
                db_engine = "postgresql"
            elif db_type.startswith("mssql"):
                db_engine = "mssql+pymssql"
            elif db_type.startswith("influx"):
                db_engine = "influxdb"
            elif db_type.startswith("sqlite"):
                db_engine = "sqlite"
        if db_engine is not None and db_engine.startswith("sqlite"):
            uri = f"{db_engine}://{db_name}"
        else:
            engine = db_engine or Database.DEFAULT_ENGINE
            user = db_user or Database.DEFAULT_USER
            password = db_password or Database.DEFAULT_PW
            host = db_host or Database.DEFAULT_HOST
            port = db_port or Database.DEFAULT_PORT
            name = db_name or Database.DEFAULT_DB
            uri = f"{engine}://{user}:{password}@{host}:{port}/{name}"

        connection_info = {
            "dbName": db_name if db_name is not None else Database.DEFAULT_DB,
            "dbUser": db_user if db_user is not None else Database.DEFAULT_USER,
            "dbPassword": db_password if db_password is not None else Database.DEFAULT_PW,
            "dbHost": db_host if db_host is not None else Database.DEFAULT_HOST,
            "dbPort": db_port if db_port is not None else Database.DEFAULT_PORT,
            "dbTimeout": db_timeout if db_timeout is not None else Database.DEFAULT_TIMEOUT,
            "dbSchema": db_schema if db_schema is not None else Database.DEFAULT_SCHEMA,
            "dbEngine": db_engine if db_engine is not None else Database.DEFAULT_ENGINE,
            "uri": uri,
            "applicationName": ce("DATABASE_APPLICATION_NAME", "pygarden"),
        }
        return connection_info
