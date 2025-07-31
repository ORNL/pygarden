#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a MultiDatabase class using multiple Database Mixins."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Callable, Optional, Type, Union
from uuid import uuid4

from pygarden.env import mock_env_vars
from pygarden.logz import create_logger

if TYPE_CHECKING:
    from pygarden.mixins.influx import InfluxMixin
    from pygarden.mixins.mssql import MSSQLMixin
    from pygarden.mixins.postgres import PostgresMixin
    from pygarden.mixins.sqlite import SQLiteMixin


class MultiDatabase:
    """Provide a MultiDatabase class using multiple Database Mixins."""

    def __init__(self, configs: list[dict]):
        """
        Initialize the MultiDatabase class with a list of database configurations.

        :param configs: a list of dictionaries containing database configurations
        """
        self.databases = {}
        self.logger = create_logger()
        for config in configs:
            db_type: str = config.get("type")
            db_id: str = config.get("id", str(uuid4()))
            self.logger.debug(f"Creating {db_type} database with id {db_id}")
            config = self._rename_env_vars(config)
            with mock_env_vars(config):
                from pygarden.database import Database

                mixin = self._get_mixin_for_type(db_type=db_type)
                if mixin:
                    conn_info = Database.create_connection_info(
                        db_name=config.get("DATABASE_DB", None),
                        db_user=config.get("DATABASE_USER", None),
                        db_password=config.get("DATABASE_PW", None),
                        db_host=config.get("DATABASE_HOST", None),
                        db_port=config.get("DATABASE_PORT", None),
                        db_type=db_type,
                    )
                    db_instance = type(db_type.capitalize() + "DB", (mixin, Database), {})(connection_info=conn_info)
                    self.databases[db_id] = db_instance
                else:
                    self.logger.warning(f"Skipping unknown Database type: {db_type}")

    @staticmethod
    def _rename_env_vars(config):
        def get_pref_value(config, keys, default=None):
            for key in keys:
                if key in config:
                    return config[key]
            return default

        new_config = {}

        # Define mappings of old keys to new keys
        key_mappings = {
            "host": "DATABASE_HOST",
            "dbHost": "DATABASE_HOST",
            "port": "DATABASE_PORT",
            "dbPort": "DATABASE_PORT",
            "db": "DATABASE_DB",
            "database": "DATABASE_DB",
            "dbName": "DATABASE_DB",
            "user": "DATABASE_USER",
            "dbUser": "DATABASE_USER",
            "pw": "DATABASE_PW",
            "password": "DATABASE_PW",
            "pass": "DATABASE_PW",
            "dbPass": "DATABASE_PW",
            "dbPassword": "DATABASE_PW",
        }

        # Rename keys and pop old keys if replacements exist
        for old_key, new_key in key_mappings.items():
            new_value = get_pref_value(config, [old_key])
            if new_value is not None:
                new_config[new_key] = new_value
                config.pop(old_key, None)

        # Update config with new entries
        config.update(new_config)

        return config

    @staticmethod
    def _get_mixin_for_type(
        db_type: str,
    ) -> Optional[Type[Union[PostgresMixin, MSSQLMixin, InfluxMixin, SQLiteMixin]]]:
        """
        Get the appropriate mixin class for the given database type.

        :param db_type: the type of database to initialize
        :return:
        """
        db_type = db_type.lower()
        if db_type.startswith("postgres") or db_type.startswith("pg"):
            from pygarden.mixins.postgres import PostgresMixin

            return PostgresMixin
        if db_type.startswith("mssql"):
            from pygarden.mixins.mssql import MSSQLMixin

            return MSSQLMixin
        if db_type.startswith("influx"):
            from pygarden.mixins.influx import InfluxMixin

            return InfluxMixin
        if db_type.startswith("sqlite"):
            from pygarden.mixins.sqlite import SQLiteMixin

            return SQLiteMixin

        # add more database Mixins here as they become available
        return None

    def open(self):
        """Open all databases in parallel."""
        with ThreadPoolExecutor(max_workers=len(self.databases)) as executor:
            for db in self.databases.values():
                executor.submit(db.open)

    def close(self):
        """Close all databases in parallel."""
        with ThreadPoolExecutor(max_workers=len(self.databases)) as executor:
            for db in self.databases.values():
                executor.submit(db.close)

    def query(self, query):
        """Query multiple databases in parallel."""
        results = {}
        with ThreadPoolExecutor(max_workers=len(self.databases)) as executor:
            future_to_db_id = {executor.submit(db.query, query): db_id for db_id, db in self.databases.items()}
            for future in future_to_db_id:
                db_id = future_to_db_id[future]
                results[db_id] = future.result()
        return results

    def transform_and_transfer(
        self,
        from_db_id: str,
        to_db_id: str,
        select_query: str,
        insert_query_template: str,
        transform_func: Optional[Callable] = None,
    ):
        """
        Converts data from a PostgreSQL database to a Microsoft SQL Server database.

        :param from_db_id: The ID of the PostgreSQL database.
        :param to_db_id: The ID of the SQL Server database.
        :param select_query: SQL query to select data from PostgreSQL.
        :param insert_query_template: SQL template for inserting data into SQL Server.
        :param transform_func: Optional function to transform data before inserting into SQL Server.
        :return: True if the conversion was successful, False otherwise.
        """
        try:
            # Execute the select query on PostgreSQL
            source_results = self.databases[from_db_id].query(select_query)
            if not source_results:
                self.logger.info(f"No data found to convert from {from_db_id}.")
                return False

            operations = []
            for row in source_results:
                transformed_row = transform_func(row) if transform_func else row
                insert_query = insert_query_template.format(*transformed_row)
                operations.append(insert_query)

            # Insert data into SQL Server
            self._execute_parallel_db_operations(to_db_id, operations)

            self.logger.info(f"Data conversion from {from_db_id} to {to_db_id} completed successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to convert data from {from_db_id} to {to_db_id}: {e}")
            return False

    def _execute_parallel_db_operations(self, db_id: str, operations: list):
        """
        Executes database operations in parallel.

        Args:
        ----
            db_id (str): the ID of the database to execute operations in SQL
            operations (list): A list of SQL operations to execute
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(self.databases[db_id].query, op) for op in operations]
            for future in futures:
                future.result()  # this will raise an exception if any op fails, may want to catch and report
