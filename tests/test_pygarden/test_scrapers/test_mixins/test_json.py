"""Tests for the JsonMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.json import JsonMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithJson(JsonMixin, Scraper):
    """Test scraper using JsonMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": data}


class TestJsonMixin:
    """Test cases for the JsonMixin."""

    def test_json_mixin_initialization(self, tmp_path, monkeypatch):
        """Test JsonMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithJson("https://httpbin.org/json")
        assert scraper.url == "https://httpbin.org/json"

    @patch("pygarden.scrapers.mixins.json.requests.request")
    def test_json_mixin_request_method(self, mock_request, tmp_path, monkeypatch):
        """Test JsonMixin request method returns JSON object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value", "number": 42}
        mock_request.return_value = mock_response

        scraper = TestScraperWithJson("https://httpbin.org/json")
        result = scraper.request("https://httpbin.org/json", method="GET")
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42

    @patch("pygarden.scrapers.mixins.json.requests.request")
    def test_json_mixin_request_with_post(self, mock_request, tmp_path, monkeypatch):
        """Test JsonMixin request method with POST method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        scraper = TestScraperWithJson("https://httpbin.org/post")
        result = scraper.request("https://httpbin.org/post", method="POST")
        assert isinstance(result, dict)
        assert result["status"] == "success"

    @patch("pygarden.scrapers.mixins.json.requests.request")
    def test_json_mixin_request_with_kwargs(self, mock_request, tmp_path, monkeypatch):
        """Test JsonMixin request method with additional kwargs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response

        scraper = TestScraperWithJson("https://httpbin.org/json")
        result = scraper.request("https://httpbin.org/json", method="GET", headers={"X-Test": "value"})
        assert isinstance(result, dict)
        mock_request.assert_called_once()


