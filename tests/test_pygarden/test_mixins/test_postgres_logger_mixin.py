"""Tests for PostgresLoggerMixin."""

from unittest.mock import MagicMock

import pytest

from pygarden.mixins.postgres_logger import PostgresLoggerMixin


@pytest.fixture
def logger_mixin():
    """Create a PostgresLoggerMixin with mocked database behavior."""
    mixin = PostgresLoggerMixin()

    mixin.cursor = MagicMock()
    mixin.open = MagicMock()
    mixin.close = MagicMock()
    mixin.logger = MagicMock()

    return mixin


def test_defaults(logger_mixin):
    assert logger_mixin.schema == "public"
    assert logger_mixin.table_name == "log"
    assert logger_mixin.log_collection == []


def test_custom_schema_and_table_name():
    mixin = PostgresLoggerMixin(schema="test_schema", table_name="custom_log")

    assert mixin.schema == "test_schema"
    assert mixin.table_name == "custom_log"


@pytest.mark.parametrize(
    "method_name,level",
    [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
        ("error", "ERROR"),
        ("critical", "CRITICAL"),
        ("exception", "EXCEPTION"),
    ],
)
def test_log_methods_write_to_database(logger_mixin, method_name, level):
    logger_mixin.check_table_exists = MagicMock()
    logger_mixin.log_to_database = MagicMock()

    getattr(logger_mixin, method_name)("test message", w=True)

    logger_mixin.check_table_exists.assert_called_once_with()
    logger_mixin.log_to_database.assert_called_once_with(level, "test message")
    getattr(logger_mixin.logger, method_name).assert_called_once_with("test message")


@pytest.mark.parametrize(
    "method_name,level",
    [
        ("debug", "DEBUG"),
        ("info", "INFO"),
        ("warning", "WARNING"),
        ("error", "ERROR"),
        ("critical", "CRITICAL"),
        ("exception", "EXCEPTION"),
    ],
)
def test_log_methods_collect_logs(logger_mixin, method_name, level):
    getattr(logger_mixin, method_name)("test message", c=True)

    assert logger_mixin.log_collection == [(level, "test message")]
    getattr(logger_mixin.logger, method_name).assert_called_once_with("test message")


@pytest.mark.parametrize(
    "method_name",
    ["debug", "info", "warning", "error", "critical", "exception"],
)
def test_log_methods_only_log_to_logger_by_default(logger_mixin, method_name):
    logger_mixin.check_table_exists = MagicMock()
    logger_mixin.log_to_database = MagicMock()
    logger_mixin.collect_logs = MagicMock()

    getattr(logger_mixin, method_name)("test message")

    logger_mixin.check_table_exists.assert_not_called()
    logger_mixin.log_to_database.assert_not_called()
    logger_mixin.collect_logs.assert_not_called()
    getattr(logger_mixin.logger, method_name).assert_called_once_with("test message")


def test_check_table_exists(logger_mixin):
    logger_mixin.check_table_exists()

    logger_mixin.open.assert_called_once_with()
    logger_mixin.cursor.execute.assert_called_once()

    query = logger_mixin.cursor.execute.call_args.args[0]

    assert "CREATE TABLE IF NOT EXISTS public.log" in query
    assert "levelname TEXT" in query
    assert "message TEXT" in query
    assert "ts TIMESTAMPTZ DEFAULT NOW()" in query

    logger_mixin.close.assert_called_once_with()


def test_log_to_database(logger_mixin):
    logger_mixin.log_to_database("INFO", "test message")

    logger_mixin.open.assert_called_once_with()
    logger_mixin.cursor.execute.assert_called_once_with(
        """
            INSERT INTO public.log (levelname, message)
            VALUES (%s, %s);
            """,
        ("INFO", "test message"),
    )
    logger_mixin.close.assert_called_once_with()


def test_collect_logs(logger_mixin):
    logger_mixin.collect_logs("INFO", "test message")

    assert logger_mixin.log_collection == [("INFO", "test message")]


def test_write_log_collection_to_database_with_log_list(logger_mixin):
    logger_mixin.check_table_exists = MagicMock()

    logger_mixin.write_log_collection_to_database(
        [
            ("INFO", "message one"),
            ("ERROR", "message two"),
        ]
    )

    logger_mixin.check_table_exists.assert_called_once_with()
    logger_mixin.open.assert_called_once_with()

    assert logger_mixin.cursor.execute.call_count == 2
    logger_mixin.cursor.execute.assert_any_call(
        """
                    INSERT INTO public.log
                    (levelname, message)
                    VALUES (%s, %s);
                    """,
        ("INFO", "message one"),
    )
    logger_mixin.cursor.execute.assert_any_call(
        """
                    INSERT INTO public.log
                    (levelname, message)
                    VALUES (%s, %s);
                    """,
        ("ERROR", "message two"),
    )

    logger_mixin.close.assert_called_once_with()


def test_write_log_collection_to_database_with_internal_collection(logger_mixin):
    logger_mixin.check_table_exists = MagicMock()
    logger_mixin.log_collection = [
        ("INFO", "message one"),
        ("WARNING", "message two"),
    ]

    logger_mixin.write_log_collection_to_database()

    logger_mixin.check_table_exists.assert_called_once_with()
    logger_mixin.open.assert_called_once_with()

    assert logger_mixin.cursor.execute.call_count == 2
    assert logger_mixin.log_collection == []

    logger_mixin.close.assert_called_once_with()


def test_write_log_collection_to_database_with_no_logs(logger_mixin):
    logger_mixin.check_table_exists = MagicMock()
    logger_mixin.warning = MagicMock()

    logger_mixin.write_log_collection_to_database()

    logger_mixin.check_table_exists.assert_called_once_with()
    logger_mixin.open.assert_called_once_with()
    logger_mixin.cursor.execute.assert_not_called()
    logger_mixin.warning.assert_called_once_with("No logs recorded.")
    logger_mixin.close.assert_called_once_with()


def test_queries_use_custom_schema_and_table_name(logger_mixin):
    logger_mixin.schema = "custom_schema"
    logger_mixin.table_name = "custom_log"

    logger_mixin.check_table_exists()

    create_query = logger_mixin.cursor.execute.call_args.args[0]

    assert "CREATE TABLE IF NOT EXISTS custom_schema.custom_log" in create_query

    logger_mixin.cursor.execute.reset_mock()
    logger_mixin.open.reset_mock()
    logger_mixin.close.reset_mock()

    logger_mixin.log_to_database("INFO", "test message")

    insert_query = logger_mixin.cursor.execute.call_args.args[0]

    assert "INSERT INTO custom_schema.custom_log" in insert_query
    assert logger_mixin.cursor.execute.call_args.args[1] == ("INFO", "test message")