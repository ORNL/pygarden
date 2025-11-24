"""Tests for the CfscrapeMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.cfscrape import CfscrapeMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithCfscrape(CfscrapeMixin, Scraper):
    """Test scraper using CfscrapeMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestCfscrapeMixin:
    """Test cases for the CfscrapeMixin."""

    def test_cfscrape_mixin_initialization(self, tmp_path, monkeypatch):
        """Test CfscrapeMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithCfscrape("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.cfscrape.cfscrape")
    def test_cfscrape_mixin_request_method(self, mock_cfscrape_module, tmp_path, monkeypatch):
        """Test CfscrapeMixin request method returns BeautifulSoup object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_scraper.get.return_value = mock_response
        mock_cfscrape_module.create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCfscrape("https://example.com")
        result = scraper.request("https://example.com", verify=False)
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("h1") is not None
        mock_scraper.get.assert_called_once_with("https://example.com")

    @patch("pygarden.scrapers.mixins.cfscrape.cfscrape")
    def test_cfscrape_mixin_request_with_verify(self, mock_cfscrape_module, tmp_path, monkeypatch):
        """Test CfscrapeMixin request method with verify parameter."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_scraper.get.return_value = mock_response
        mock_cfscrape_module.create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCfscrape("https://example.com")
        result = scraper.request("https://example.com", verify=True)
        assert result is not None
        assert mock_scraper.verify is True

    @patch("pygarden.scrapers.mixins.cfscrape.cfscrape")
    def test_cfscrape_mixin_request_with_kwargs(self, mock_cfscrape_module, tmp_path, monkeypatch):
        """Test CfscrapeMixin request method with additional kwargs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_scraper.get.return_value = mock_response
        mock_cfscrape_module.create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCfscrape("https://example.com")
        result = scraper.request("https://example.com", verify=False, delay=5)
        assert result is not None
        mock_cfscrape_module.create_scraper.assert_called_once_with(delay=5)

