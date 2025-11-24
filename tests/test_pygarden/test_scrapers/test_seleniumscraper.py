"""Tests for the SeleniumScraper class."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.seleniumscraper import SeleniumScraper


class ConcreteSeleniumScraper(SeleniumScraper):
    """Concrete implementation of SeleniumScraper for testing."""

    def parse(self, data):
        """Parse method implementation."""
        if data is None:
            return None
        return {"parsed": True, "data": str(data)}

    def interact(self, web_driver):
        """Interact method implementation."""
        return "<html><body>Test</body></html>"


class TestSeleniumScraper:
    """Test cases for the SeleniumScraper class."""

    def test_selenium_scraper_initialization(self, tmp_path, monkeypatch):
        """Test SeleniumScraper initialization."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = ConcreteSeleniumScraper("https://example.com")
        assert scraper.url == "https://example.com"

    def test_selenium_scraper_interact_not_implemented(self, tmp_path, monkeypatch):
        """Test that SeleniumScraper cannot be instantiated without interact method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        with pytest.raises(TypeError):
            SeleniumScraper("https://example.com")

    @patch("pygarden.scrapers.seleniumscraper.WebDriver")
    def test_selenium_scraper_request(self, mock_webdriver, tmp_path, monkeypatch):
        """Test SeleniumScraper request method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_wd = MagicMock()
        mock_wd.__enter__ = MagicMock(return_value=mock_wd)
        mock_wd.__exit__ = MagicMock(return_value=None)
        mock_webdriver.return_value = mock_wd
        scraper = ConcreteSeleniumScraper("https://example.com")
        result = scraper.request("https://example.com")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object

    @patch("pygarden.scrapers.seleniumscraper.WebDriver")
    def test_selenium_scraper_request_with_none_interact(self, mock_webdriver, tmp_path, monkeypatch):
        """Test SeleniumScraper request method when interact returns None."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))

        class NoInteractScraper(SeleniumScraper):
            def parse(self, data):
                return {"parsed": True}

            def interact(self, web_driver):
                return None

        mock_wd = MagicMock()
        mock_wd.__enter__ = MagicMock(return_value=mock_wd)
        mock_wd.__exit__ = MagicMock(return_value=None)
        mock_webdriver.return_value = mock_wd
        scraper = NoInteractScraper("https://example.com")
        result = scraper.request("https://example.com")
        assert result is None


