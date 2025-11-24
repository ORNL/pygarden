"""Tests for the XmlSoupMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.xml_soup import XmlSoupMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithXmlSoup(XmlSoupMixin, Scraper):
    """Test scraper using XmlSoupMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestXmlSoupMixin:
    """Test cases for the XmlSoupMixin."""

    def test_xml_soup_mixin_initialization(self, tmp_path, monkeypatch):
        """Test XmlSoupMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithXmlSoup("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.xml_soup.requests.request")
    def test_xml_soup_mixin_request_html(self, mock_request, tmp_path, monkeypatch):
        """Test XmlSoupMixin request_html static method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><root>Test</root>'
        mock_request.return_value = mock_response

        result = XmlSoupMixin.request_html("https://example.com/xml", method="GET")
        assert result == '<?xml version="1.0"?><root>Test</root>'

    @patch("pygarden.scrapers.mixins.xml_soup.requests.request")
    def test_xml_soup_mixin_request(self, mock_request, tmp_path, monkeypatch):
        """Test XmlSoupMixin request method returns BeautifulSoup object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><root><item>Test</item></root>'
        mock_request.return_value = mock_response

        scraper = TestScraperWithXmlSoup("https://example.com/xml")
        # Use html.parser instead of lxml to avoid dependency issues in tests
        result = scraper.request("https://example.com/xml", method="GET", parser="html.parser")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("item") is not None

    @patch("pygarden.scrapers.mixins.xml_soup.requests.request")
    def test_xml_soup_mixin_request_custom_parser(self, mock_request, tmp_path, monkeypatch):
        """Test XmlSoupMixin request method with custom parser."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><root>Test</root>'
        mock_request.return_value = mock_response

        scraper = TestScraperWithXmlSoup("https://example.com/xml")
        result = scraper.request("https://example.com/xml", method="GET", parser="html.parser")
        assert result is not None

