"""Tests for the CloudscraperMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.cloudscraper import CloudscraperMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithCloudscraper(CloudscraperMixin, Scraper):
    """Test scraper using CloudscraperMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data) if data else None}


class TestCloudscraperMixin:
    """Test cases for the CloudscraperMixin."""

    def test_cloudscraper_mixin_initialization(self, tmp_path, monkeypatch):
        """Test CloudscraperMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithCloudscraper("https://example.com")
        assert scraper.url == "https://example.com"

    @patch("pygarden.scrapers.mixins.cloudscraper.cloudscraper.create_scraper")
    def test_cloudscraper_mixin_request_success(self, mock_create_scraper, tmp_path, monkeypatch):
        """Test CloudscraperMixin request method returns BeautifulSoup object when no captcha."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_scraper.get.return_value = mock_response
        mock_create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCloudscraper("https://example.com")
        result = scraper.request("https://example.com", n_retries=3)
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        assert result.find("h1") is not None

    @patch("pygarden.scrapers.mixins.cloudscraper.cloudscraper.create_scraper")
    def test_cloudscraper_mixin_request_with_captcha(self, mock_create_scraper, tmp_path, monkeypatch):
        """Test CloudscraperMixin request method returns None when captcha is detected."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body>captcha challenge</body></html>"
        mock_scraper.get.return_value = mock_response
        mock_create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCloudscraper("https://example.com")
        result = scraper.request("https://example.com", n_retries=2)
        assert result is None

    @patch("pygarden.scrapers.mixins.cloudscraper.cloudscraper.create_scraper")
    def test_cloudscraper_mixin_request_retries(self, mock_create_scraper, tmp_path, monkeypatch):
        """Test CloudscraperMixin request method retries on captcha detection."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_scraper = MagicMock()
        # First two responses have captcha, third succeeds
        mock_response1 = MagicMock()
        mock_response1.text = "<html><body>captcha challenge</body></html>"
        mock_response2 = MagicMock()
        mock_response2.text = "<html><body>captcha challenge</body></html>"
        mock_response3 = MagicMock()
        mock_response3.text = "<html><body><h1>Success</h1></body></html>"
        mock_scraper.get.side_effect = [mock_response1, mock_response2, mock_response3]
        mock_create_scraper.return_value = mock_scraper

        scraper = TestScraperWithCloudscraper("https://example.com")
        result = scraper.request("https://example.com", n_retries=3)
        assert result is not None
        assert result.find("h1") is not None
        assert mock_scraper.get.call_count == 3


