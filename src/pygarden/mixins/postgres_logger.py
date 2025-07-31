"""Provide a logger mixin for PostgreSQL."""

from pygarden.database import Database
from pygarden.mixins.postgres import PostgresMixin


class PostgresLoggerMixin(Database, PostgresMixin):
    """
    Log Handler for easy logging.

    The intent of this handler is to have a common place to easily print logs
    to the terminal and/or record them to the .log table of a schema. After
    initializing the class, passing the w parameter to the log function will tell
    the function to write the log to the database, for example:
    db_logger.info("TEST MESSAGE", w=True)

    Attributes
    ----------
        schema (str): The name of the schema

    """

    def __init__(self, schema: str, **kwargs):
        """
        The constructor for the PostgresLoggerMixin class.

        :param schema: The name of the schema
        :param kwargs: Additional keyword arguments.
        """
        super().__init__()
        self.schema = schema
        self.log_collection = []
        self.logger = Database().logger

    def debug(self, message, w=False, c=False):
        """Logs a debug message."""
        if w:
            self.check_table_exists()
            self.log_to_database("DEBUG", message)
        elif c:
            self.collect_logs("DEBUG", message)
        self.logger.debug(message)

    def info(self, message, w=False, c=False):
        """Logs an info message."""
        if w:
            self.check_table_exists()
            self.log_to_database("INFO", message)
        elif c:
            self.collect_logs("INFO", message)
        self.logger.info(message)

    def warning(self, message, w=False, c=False):
        """Logs a warning message."""
        if w:
            self.check_table_exists()
            self.log_to_database("WARNING", message)
        elif c:
            self.collect_logs("WARNING", message)
        self.logger.warning(message)

    def error(self, message, w=False, c=False):
        """Logs an error message."""
        if w:
            self.check_table_exists()
            self.log_to_database("ERROR", message)
        elif c:
            self.collect_logs("ERROR", message)
        self.logger.error(message)

    def critical(self, message, w=False, c=False):
        """Logs a critical Message"""
        if w:
            self.check_table_exists()
            self.log_to_database("CRITICAL", message)
        elif c:
            self.collect_logs("CRITICAL", message)
        self.logger.critical(message)

    # Only call from an exception handler
    def exception(self, message, w=False, c=False):
        """Logs and exception message."""
        if w:
            self.check_table_exists()
            self.log_to_database("EXCEPTION", message)
        elif c:
            self.collect_logs("EXCEPTION", message)
        self.logger.exception(message)

    def check_table_exists(self):
        """Checks if log table exists for workspace."""
        self.open()
        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {self.schema}.log (levelname TEXT, message TEXT, ts timestamp default now());"
        )
        self.close()

    def log_to_database(self, loglevel, message):
        """Logs log message to database."""
        self.open()
        self.cursor.execute(f"INSERT INTO {self.schema}.log (levelname, message) VALUES('{loglevel}', '{message}');")
        self.close()

    def collect_logs(self, level, message):
        """Appends log messages to list"""
        log = (level, message)
        self.log_collection.append(tuple(log))

    def write_log_collection_to_database(self, log_list=None):
        """Writes collection of logs to database and empties log list"""
        self.check_table_exists()
        # This keeps us from mucking up the internal list, even though we double
        # the code
        self.open()
        if log_list:
            for log_entry in log_list:
                self.cursor.execute(f"INSERT INTO {self.schema}.log VALUES('{log_entry[0]}', '{log_entry[1]}');")
        elif self.log_collection:
            for log_entry in self.log_collection:
                self.cursor.execute(f"INSERT INTO {self.schema}.log VALUES('{log_entry[0]}', '{log_entry[1]}');")
            self.log_collection = []
        else:
            self.warning("No logs recorded.")
        self.close()
