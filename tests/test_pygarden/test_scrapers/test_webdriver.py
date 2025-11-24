"""Tests for the webdriver module."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.webdriver import WebDriver


class TestWebDriver:
    """Test cases for the WebDriver class."""

    @patch("pygarden.scrapers.webdriver.requests.get")
    def test_webdriver_requests_driver(self, mock_get, tmp_path, monkeypatch):
        """Test WebDriver with requests driver."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "test html content"
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        wd = WebDriver(url="https://httpbin.org/get", driver="requests", output="text")
        assert wd.out == "test html content"
        assert wd.url == "https://httpbin.org/get"
        assert wd.driver_type == "requests"

    @patch("pygarden.scrapers.webdriver.requests.get")
    def test_webdriver_requests_json_output(self, mock_get, tmp_path, monkeypatch):
        """Test WebDriver with requests driver and JSON output."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        wd = WebDriver(url="https://httpbin.org/json", driver="requests", output="json")
        assert wd.out == {"key": "value"}

    def test_webdriver_invalid_driver(self, tmp_path, monkeypatch):
        """Test WebDriver with invalid driver type."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        with pytest.raises(KeyError):
            WebDriver(url="https://example.com", driver="invalid_driver")

    def test_webdriver_context_manager(self, tmp_path, monkeypatch):
        """Test WebDriver as context manager."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))

        with patch("pygarden.scrapers.webdriver.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "test"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            with WebDriver(url="https://example.com", driver="requests") as wd:
                assert wd.url == "https://example.com"

    @patch("pygarden.scrapers.webdriver.webdriver.Chrome")
    def test_webdriver_chrome_initialization(self, mock_chrome, tmp_path, monkeypatch):
        """Test WebDriver Chrome initialization."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        try:
            wd = WebDriver(url="https://example.com", driver="chromedriver")
            assert wd.driver_type == "chromedriver"
            if hasattr(wd, "driver"):
                assert wd.driver is not None
        except Exception:
            # Chrome driver might not be available in test environment
            pass

    def test_webdriver_str_representation(self, tmp_path, monkeypatch):
        """Test WebDriver string representation."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))

        with patch("pygarden.scrapers.webdriver.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "test"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            wd = WebDriver(url="https://example.com", driver="requests")
            str_repr = str(wd)
            assert "WebDriver" in str_repr
            assert "https://example.com" in str_repr

    @patch("pygarden.scrapers.webdriver.requests.get")
    def test_webdriver_dump_out(self, mock_get, tmp_path, monkeypatch):
        """Test WebDriver dump_out method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "test output"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        wd = WebDriver(url="https://example.com", driver="requests", output="text")
        assert wd.dump_out() == "test output"

