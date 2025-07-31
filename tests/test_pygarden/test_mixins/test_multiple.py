"""Test the MultiDatabase mixin."""

import pytest
from pygarden.mixins.multiple import MultiDatabase


@pytest.fixture
def multi_database_fixture():
    """Create a fixture for MultiDatabase."""
    infl_id = "influx_id"
    influx = {
        "type": "influx",
        "id": infl_id,
        "host": "influx",
        "user": "influx",
        "password": "secret",
        "database": "something",
        "port": "8086",
    }

    pg_id = "pg_db"
    postgres = {
        "type": "postgres",
        "id": pg_id,
        "host": "localhost",
        "user": "me",
        "password": "nevergonnaguess",
        "database": "db",
        "port": "5435",
    }

    configs = [influx, postgres]
    multi = MultiDatabase(configs)
    return multi, pg_id, infl_id


def test_postgres_uri(multi_database_fixture):
    """Test the PostgreSQL URI generation."""
    multi, pg_id, infl_id = multi_database_fixture
    pg_expected_uri = "postgresql://me:nevergonnaguess@localhost:5435/db"
    actual_pg_uri = multi.databases[pg_id].connection_info["uri"]
    assert actual_pg_uri == pg_expected_uri


def test_influx_uri(multi_database_fixture):
    """Test the InfluxDB URI generation."""
    multi, pg_id, infl_id = multi_database_fixture
    influx_expected_uri = "influxdb://influx:secret@influx:8086/something"
    actual_influx_uri = multi.databases[infl_id].connection_info["uri"]
    assert actual_influx_uri == influx_expected_uri


if __name__ == "__main__":
    pytest.main()
