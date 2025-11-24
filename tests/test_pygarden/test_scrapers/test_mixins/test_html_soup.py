"""Tests for the HtmlSoupMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.html_soup import HtmlSoupMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithHtmlSoup(HtmlSoupMixin, Scraper):
    """Test scraper using HtmlSoupMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestHtmlSoupMixin:
    """Test cases for the HtmlSoupMixin."""

    def test_html_soup_mixin_initialization(self, tmp_path, monkeypatch):
        """Test HtmlSoupMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithHtmlSoup("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.html_soup.requests.request")
    def test_html_soup_mixin_request_html(self, mock_request, tmp_path, monkeypatch):
        """Test HtmlSoupMixin request_html method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_request.return_value = mock_response

        scraper = TestScraperWithHtmlSoup("https://example.com")
        result = scraper.request_html("https://example.com", method="GET")
        assert result == "<html><body>Test</body></html>"

    @patch("pygarden.scrapers.mixins.html_soup.requests.request")
    def test_html_soup_mixin_request(self, mock_request, tmp_path, monkeypatch):
        """Test HtmlSoupMixin request method returns BeautifulSoup object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Test</p></body></html>"
        mock_request.return_value = mock_response

        scraper = TestScraperWithHtmlSoup("https://example.com")
        result = scraper.request("https://example.com", method="GET", parser="html.parser")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("p") is not None

    @patch("pygarden.scrapers.mixins.html_soup.requests.request")
    def test_html_soup_mixin_request_custom_parser(self, mock_request, tmp_path, monkeypatch):
        """Test HtmlSoupMixin request method with custom parser."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_request.return_value = mock_response

        scraper = TestScraperWithHtmlSoup("https://example.com")
        # Use html.parser instead of lxml to avoid dependency issues in tests
        result = scraper.request("https://example.com", method="GET", parser="html.parser")
        assert result is not None

