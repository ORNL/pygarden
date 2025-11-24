"""Tests for the HtmlMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.html import HtmlMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithHtml(HtmlMixin, Scraper):
    """Test scraper using HtmlMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestHtmlMixin:
    """Test cases for the HtmlMixin."""

    def test_html_mixin_initialization(self, tmp_path, monkeypatch):
        """Test HtmlMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithHtml("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.html.requests.request")
    def test_html_mixin_request_method(self, mock_request, tmp_path, monkeypatch):
        """Test HtmlMixin request method returns BeautifulSoup object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_request.return_value = mock_response

        scraper = TestScraperWithHtml("https://example.com")
        result = scraper.request("https://example.com", method="GET")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("h1") is not None

    @patch("pygarden.scrapers.mixins.html.requests.request")
    def test_html_mixin_request_with_post(self, mock_request, tmp_path, monkeypatch):
        """Test HtmlMixin request method with POST method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "<html><body>POST Response</body></html>"
        mock_request.return_value = mock_response

        scraper = TestScraperWithHtml("https://httpbin.org/post")
        result = scraper.request("https://httpbin.org/post", method="POST")
        assert result is not None
        mock_request.assert_called_once()
        # Check that method was passed correctly (as keyword argument)
        call_kwargs = mock_request.call_args[1] if mock_request.call_args[1] else {}
        call_pos_args = mock_request.call_args[0] if mock_request.call_args[0] else ()
        # requests.request can take method as first positional or as keyword
        method_value = call_kwargs.get("method", call_pos_args[0] if call_pos_args else None)
        assert method_value.upper() == "POST"

