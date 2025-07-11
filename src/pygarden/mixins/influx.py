"""InfluxDB Mixin for pygarden."""

try:
    from influxdb import InfluxDBClient
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn("Influx extra must be installed to use influx mixin. ")
    sys.exit(1)

from pygarden.env import check_environment as ce


class InfluxMixin:
    """Serve common connection method for InfluxDB."""

    DEFAULT_HOST = ce("DATABASE_HOST_IN", ce("DATABASE_DB", ce("INFLUXDB_HOST", "localhost")))
    DEFAULT_PORT = int(ce("DATABASE_PORT_IN", ce("DATABASE_PORT", ce("INFLUXDB_PORT", 8086))))
    DEFAULT_USER = ce("DATABASE_USER_IN", ce("DATABASE_USER", ce("INFLUXDB_ADMIN_USER", "admin")))
    DEFAULT_PASSWORD = ce("DATABASE_PW_IN", ce("DATABASE_PW", ce("INFLUXDB_ADMIN_PASSWORD", "secret")))
    DEFAULT_DB = ce("DATABASE_DB_IN", ce("DATABASE_DB", ce("INFLUX_DB", "cast")))

    def open(self):
        """Create the InfluxDB client instance.

        :returns: True if connection successful, False otherwise.
        :rtype: bool
        """
        db_name = self.connection_info.get("dbName", InfluxMixin.DEFAULT_DB)
        db_user = self.connection_info.get("dbUser", InfluxMixin.DEFAULT_USER)
        db_password = self.connection_info.get("dbPassword", InfluxMixin.DEFAULT_PASSWORD)
        db_host = self.connection_info.get("dbHost", InfluxMixin.DEFAULT_HOST)
        db_port = self.connection_info.get("dbPort", InfluxMixin.DEFAULT_PORT)

        self.logger.debug("Creating InfluxDB Client Instance")
        try:
            self.client = InfluxDBClient(
                host=db_host,
                port=db_port,
                username=db_user,
                password=db_password,
                database=db_name,
            )
            self.logger.debug("Successfully created InfluxDB client instance")
        except Exception as error:
            self.logger.error(f"Error creating InfluxDB Client: {error}")
            return False
        return True

    def query(self, query):
        """Query the InfluxDB.

        :param query: Query string to execute.
        :returns: Query results or None if failed.
        """
        if not self.client:
            self.logger.info("InfluxDB client not created, creating now.")
            if not self.open():
                return None
        self.logger.debug("Submitting query to InfluxDB.")
        try:
            result = self.client.query(query)
            return result
        except Exception as error:
            self.logger.error(f"Error during query execution: {error}")
            return None

    def list_databases(self):
        """List all databases in InfluxDB.

        :returns: List of databases or None if failed.
        """
        if not self.client:
            if not self.open():
                return None
        return self.client.get_list_database()
