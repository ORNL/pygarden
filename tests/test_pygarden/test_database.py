import types

import pytest

from pygarden.database import Database


class DummyDB(Database):
    def open(self):
        self.connection = types.SimpleNamespace()
        self.cursor = types.SimpleNamespace()
        return True

    def close(self):
        """Override close to handle our dummy objects"""
        if self.cursor:
            self.cursor = None
        if self.connection:
            self.connection = None


def test_create_connection_info_defaults():
    info = Database.create_connection_info()
    assert set(
        [
            "dbName",
            "dbUser",
            "dbPassword",
            "dbHost",
            "dbPort",
            "dbTimeout",
            "dbSchema",
            "dbEngine",
            "uri",
            "applicationName",
        ]
    ).issubset(info.keys())


def test_is_open_false_by_default():
    db = DummyDB()
    assert db.is_open() is False


def test_context_manager_opens_and_closes():
    db = DummyDB()
    with db:
        assert db.is_open() is True
    assert db.is_open() is False


def test_override_and_modify_connection_info():
    db = DummyDB()
    db.modify_connection_info("dbName", "foo")
    assert db.connection_info["dbName"] == "foo"
