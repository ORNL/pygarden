"""Tests for the RequestMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.request import RequestMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithRequest(RequestMixin, Scraper):
    """Test scraper using RequestMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestRequestMixin:
    """Test cases for the RequestMixin."""

    def test_request_mixin_initialization(self, tmp_path, monkeypatch):
        """Test RequestMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithRequest("https://httpbin.org/get")
        assert scraper.url == "https://httpbin.org/get"

    @patch("pygarden.scrapers.mixins.request.requests.request")
    def test_request_mixin_request_method(self, mock_request, tmp_path, monkeypatch):
        """Test RequestMixin request method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "test response"
        mock_request.return_value = mock_response

        scraper = TestScraperWithRequest("https://httpbin.org/get")
        result = scraper.request("https://httpbin.org/get", method="GET")
        assert result == mock_response
        mock_request.assert_called_once()

    @patch("pygarden.scrapers.mixins.request.requests.request")
    def test_request_mixin_with_kwargs(self, mock_request, tmp_path, monkeypatch):
        """Test RequestMixin request method with additional kwargs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        scraper = TestScraperWithRequest("https://httpbin.org/post")
        result = scraper.request("https://httpbin.org/post", method="POST", data={"key": "value"})
        assert result == mock_response
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert "data" in call_kwargs


