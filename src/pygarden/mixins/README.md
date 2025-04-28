The intent of the class PostgresLoggerMixin is to provide a quick and easy way to log information to both the terminal and the database. The class is of type Database from the common_package, and so leverages both the database and the logger that is created by it’s parent class, Database(), from common_package.

All one needs to initiate the PostgresLogger class is a schema name, then they would call the log just like they would normally:

	from pygarden.database import Database

    db_log = PostgresLogger(self.workspace)
    db_log.info("This is a log message", w=True)

This will log an INFO level log message and attempt to write it to the database.

Features of the this custom logging class:
Passing the -w flag will log the message to the log table of a schema in the database.
Passing the -c flag will add the log to an internal list with the intent being to dump all of the logs in the database later. For example, if you have a running loop and want to log absolutely everything, but don’t want to open and close a database connection through every iteration, simply pass the -c flag to your log method, and after your loop, run the write_log_collection_to_database(). This logs all messages in the list and clears the log collection, self.log_collection. Note that this can be leveraged without using the logger, just pass write_log_collection_to_database() a list of tuples representing log messages.

NOTE:
Note that logging provides overhead, so logging a lot of information in long running loops will slow down your functions. Just keep this in mind when deciding what you want to log.