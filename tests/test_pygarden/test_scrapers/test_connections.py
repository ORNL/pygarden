"""Tests for the connections module."""

import pytest
from unittest.mock import patch

from pygarden.scrapers.connections import create_uri


class TestConnections:
    """Test cases for the connections module."""

    def test_create_uri_defaults(self, monkeypatch):
        """Test create_uri with default environment variables."""
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.delenv("DB_PASS", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_DB", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        uri = create_uri()
        assert uri == "postgres://guest:abc123@db:5432/covidb"

    def test_create_uri_custom_values(self, monkeypatch):
        """Test create_uri with custom environment variables."""
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASS", "testpass")
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_DB", "testdb")
        monkeypatch.setenv("DB_PORT", "5433")
        uri = create_uri()
        assert uri == "postgres://testuser:testpass@localhost:5433/testdb"

    def test_create_uri_partial_custom(self, monkeypatch):
        """Test create_uri with partial custom environment variables."""
        monkeypatch.setenv("DB_USER", "customuser")
        monkeypatch.delenv("DB_PASS", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_DB", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        uri = create_uri()
        assert uri == "postgres://customuser:abc123@db:5432/covidb"


