#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allow opening with a sqlite3 connection."""

import sqlite3

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

logger = create_logger()


class SQLiteMixin:
    """
    Serve common connection method for sqlite.

    The default `search_path` is not applicable here since SQLite does not use schemas.
    """

    DEFAULT_DB = ce("DATABASE_DB_SQLITE", ce("DATABASE_DB", ":memory:"))

    def open(self):
        """
        Explicitly open the database connection

        :return: True if connection established, else False
        """
        db_name = self.connection_info.get("dbName", SQLiteMixin.DEFAULT_DB)
        self.logger.debug(f"Opening Database Connection to {db_name}")
        try:
            self.connection = sqlite3.connect(db_name)
            self.connection.row_factory = sqlite3.Row  # This enables column access by name
            self.cursor = self.connection.cursor()
            self.logger.debug("Successfully opened connection to database and created cursor")
        except sqlite3.OperationalError as error:
            self.logger.error(f"Database Error: {error}")
            return False
        return True

    def query(self, query):
        """
        Query the database.

        :param query: A valid SQL statement to send to the database.
        :return: None if query's cursor does not have a description, otherwise return the results of using `fetchall()`
        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            self.open()  # Check if it is already open
        self.logger.debug("Submitting user specified query to database.")
        try:
            self.cursor.execute(query)
            if self.cursor.description is not None:
                return [dict(row) for row in self.cursor.fetchall()]
            return None
        except sqlite3.InterfaceError as error:
            self.logger.error(f"An unexpected InterfaceError occurred: {error}")
        except sqlite3.DataError as error:
            self.logger.error(f"An unexpected DataError occurred: {error}")
        except sqlite3.IntegrityError as error:
            self.logger.error(f"An unexpected IntegrityError occurred: {error}")
        except sqlite3.ProgrammingError as error:
            self.logger.error(f"An unexpected ProgrammingError occurred: {error}")
        except sqlite3.NotSupportedError as error:
            self.logger.error(f"An unexpected NotSupportedError occurred: {error}")
        except sqlite3.DatabaseError as error:
            self.logger.error(f"An unexpected DatabaseError occurred: {error}")
        except Exception as error:
            self.logger.error("There was an undetermined issue with the query process: " + f" {error}")
        return None

    def is_open(self):
        """Check if the database connection is open."""
        return self.connection and self.cursor
