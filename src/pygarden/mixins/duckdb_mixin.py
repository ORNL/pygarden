"""Allow opening with a duckdb connection."""
try:
    import duckdb
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn(
        "DuckDB extra must be installed to use duckdb mixin. "
        "Install with 'pip install pygarden[duckdb]'"
    )
    sys.exit(1)

from pygarden.env import check_environment as ce


class DuckDBMixin:
    """
        Serve common connection method for DuckDB.

        The default schema can be set via:
            - DATABASE_SCHEMA_DUCKDB  (falls back to DATABASE_SCHEMA or 'main')
        Database path/name via:
            - DATABASE_DB_DUCKDB      (falls back to DATABASE_DB or ':memory:')
        """

    # Defaults (prefer DuckDB-specific envs, then the generic ones)
    DEFAULT_DB = ce("DATABASE_DB_DUCKDB", ce("DATABASE_DB", ":memory:"))
    DEFAULT_SCHEMA = ce("DATABASE_SCHEMA_DUCKDB", ce("DATABASE_SCHEMA", "main"))
    DEFAULT_ENGINE = ce("DATABASE_ENGINE_DUCKDB", ce("DATABASE_ENGINE", "duckdb"))
    DEFAULT_TIMEOUT = int(ce("DATABASE_TIMEOUT", 60))  # not used by duckdb, kept for parity
    DEFAULT_APPLICATION_NAME = ce("DATABASE_APPLICATION_NAME", "pygarden")  # informational only

    # For parity with other mixins; DuckDB doesn't really use a URI, but we synthesize one.
    DEFAULT_URI = f"duckdb:///{DEFAULT_DB}"

    def open(self, schema: str | None = None):
        """
        Explicitly open the DuckDB connection.

        :param schema: target schema to USE (created if not exists). Defaults to env/provided connection_info.
        :return: True if connection established, else False
        """
        # Pull from connection_info if available (populated by Database.__init__/create_connection_info)
        db_name = self.connection_info.get("dbName", DuckDBMixin.DEFAULT_DB)
        db_schema = schema or self.connection_info.get("dbSchema", DuckDBMixin.DEFAULT_SCHEMA)

        self.logger.debug("Opening DuckDB connection and creating cursor")
        self.logger.debug(self.connection_info)

        try:
            # DuckDB opens a file path or ':memory:' directly
            # Note: DuckDB ignores host/port/user/password; we keep them in connection_info for uniformity
            self.connection = duckdb.connect(database=db_name)  # autocommit by default
            self.cursor = self.connection.cursor()
            self.logger.debug("Successfully opened connection to DuckDB and created a cursor")

            # DuckDB supports schemas; default is 'main'
            # Create and switch to requested schema if provided/non-empty
            if isinstance(db_schema, str) and db_schema.strip():
                safe_schema = db_schema.strip()
                # DuckDB supports CREATE SCHEMA IF NOT EXISTS and USE <schema>;
                # USE fails if schema doesn't exist, so create first.
                self.cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}";')
                self.cursor.execute(f'USE "{safe_schema}";')
                self.logger.debug(f'Successfully set schema to "{safe_schema}"')
            else:
                self.logger.debug("No schema provided; staying on default 'main'")

        except duckdb.Error as error:
            self.logger.error(f"DuckDB Error: {error}")
            return False
        except Exception as error:
            self.logger.error(f"Unexpected error opening DuckDB: {error}")
            return False
        return True

    def _rows_to_dicts(self, cursor, rows):
        """
        Convert tuple rows to list[dict] using cursor.description for column names.
        """
        if rows is None:
            return None
        if cursor.description is None:
            return None
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]

    def query(self, query: str, *, as_dict: bool = False):
        """
        Query the DuckDB database.

        :param query: Valid SQL for DuckDB.
        :param as_dict: If True, returns list of dicts keyed by column name.
        :return: fetchall() results (list of tuples or list of dicts) or None if no resultset.
        """
        if not self.is_open():
            self.logger.info("Database not open, opening now.")
            if not self.open():
                self.logger.error("Failed to open DuckDB before querying.")
                return None

        self.logger.debug("Submitting user-specified query to DuckDB.")
        try:
            self.cursor.execute(query)
            # If the statement produces a result set
            if self.cursor.description is not None:
                rows = self.cursor.fetchall()
                return self._rows_to_dicts(self.cursor, rows) if as_dict else rows
            # No result set (DDL/DML); return None
            return None
        except duckdb.ParserException as error:
            self.logger.error(f"DuckDB ParserException: {error}")
        except duckdb.BinderException as error:
            self.logger.error(f"DuckDB BinderException: {error}")
        except duckdb.CatalogException as error:
            self.logger.error(f"DuckDB CatalogException: {error}")
        except duckdb.ConstraintException as error:
            self.logger.error(f"DuckDB ConstraintException: {error}")
        except duckdb.IOException as error:
            self.logger.error(f"DuckDB IOException: {error}")
        except duckdb.Error as error:
            self.logger.error(f"General DuckDB Error: {error}")
        except Exception as error:
            self.logger.error(f"Undetermined issue with the query process: {error}")
        return None
