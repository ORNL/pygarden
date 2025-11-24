"""Tests for the XmlMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.xml import XmlMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithXml(XmlMixin, Scraper):
    """Test scraper using XmlMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestXmlMixin:
    """Test cases for the XmlMixin."""

    def test_xml_mixin_initialization(self, tmp_path, monkeypatch):
        """Test XmlMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithXml("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.xml.requests.request")
    def test_xml_mixin_request_method(self, mock_request, tmp_path, monkeypatch):
        """Test XmlMixin request method returns BeautifulSoup object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><root><item>Test</item></root>'
        mock_request.return_value = mock_response

        scraper = TestScraperWithXml("https://example.com/xml")
        # Use html.parser instead of lxml to avoid dependency issues in tests
        result = scraper.request("https://example.com/xml", method="GET", parser="html.parser")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("item") is not None

    @patch("pygarden.scrapers.mixins.xml.requests.request")
    def test_xml_mixin_request_with_post(self, mock_request, tmp_path, monkeypatch):
        """Test XmlMixin request method with POST method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><root><status>OK</status></root>'
        mock_request.return_value = mock_response

        scraper = TestScraperWithXml("https://example.com/xml")
        # Use html.parser instead of lxml to avoid dependency issues in tests
        result = scraper.request("https://example.com/xml", method="POST", parser="html.parser")
        assert result is not None
        assert result.find("status") is not None

