"""Tests for the base Scraper class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pygarden.scrapers.scraper import Scraper


class ConcreteScraper(Scraper):
    """Concrete implementation of Scraper for testing."""

    def parse(self, data):
        """Parse method implementation."""
        if data is None:
            return None
        return {"parsed": True, "data": str(data)}


class TestScraper:
    """Test cases for the base Scraper class."""

    def test_scraper_initialization_with_string_url(self, tmp_path, monkeypatch):
        """Test scraper initialization with a string URL."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = ConcreteScraper("https://example.com")
        assert scraper.url == "https://example.com"
        assert scraper.request_args["method"] == "GET"
        assert scraper.request_args["stream"] is True
        assert scraper.request_args["allow_redirects"] is True
        assert scraper.request_args["verify"] is False

    def test_scraper_initialization_with_list_url(self, tmp_path, monkeypatch):
        """Test scraper initialization with a list of URLs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        urls = ["https://example.com", "https://httpbin.org"]
        scraper = ConcreteScraper(urls)
        assert scraper.url == urls

    def test_scraper_initialization_with_custom_method(self, tmp_path, monkeypatch):
        """Test scraper initialization with custom HTTP method."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = ConcreteScraper("https://example.com", method="POST")
        assert scraper.request_args["method"] == "POST"

    def test_scraper_initialization_creates_directories(self, tmp_path, monkeypatch):
        """Test that scraper creates data directories when not in dry run."""
        data_path = tmp_path / "data"
        raw_path = tmp_path / "raw"
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(data_path))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(raw_path))
        monkeypatch.setenv("DRY_RUN", "False")  # Explicitly set to False
        scraper = ConcreteScraper("https://example.com")
        assert data_path.exists()
        assert raw_path.exists()

    def test_scraper_dry_run_does_not_create_directories(self, tmp_path, monkeypatch):
        """Test that scraper does not create directories in dry run mode."""
        data_path = tmp_path / "data"
        raw_path = tmp_path / "raw"
        monkeypatch.setenv("DRY_RUN", "True")
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(data_path))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(raw_path))
        scraper = ConcreteScraper("https://example.com")
        assert not data_path.exists()
        assert not raw_path.exists()

    @patch("pygarden.scrapers.scraper.requests")
    def test_scraper_scrape_single_url(self, mock_requests, tmp_path, monkeypatch):
        """Test scraping a single URL."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "test data"
        mock_requests.request.return_value = mock_response
        scraper = ConcreteScraper("https://httpbin.org/get")
        scraper.request = MagicMock(return_value=mock_response)
        result = scraper.scrape()
        assert scraper.scrape_end_time is not None

    @patch("pygarden.scrapers.scraper.requests")
    def test_scraper_scrape_multiple_urls(self, mock_requests, tmp_path, monkeypatch):
        """Test scraping multiple URLs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.text = "test data"
        mock_requests.request.return_value = mock_response
        urls = ["https://httpbin.org/get", "https://httpbin.org/json"]
        scraper = ConcreteScraper(urls)
        scraper.request = MagicMock(return_value=mock_response)
        scraper.scrape()
        assert scraper.scrape_end_time is not None

    def test_scraper_parse_abstract_method(self, tmp_path, monkeypatch):
        """Test that Scraper cannot be instantiated directly."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        with pytest.raises(TypeError):
            Scraper("https://example.com")

    def test_save_raw_pages_with_override(self, tmp_path, monkeypatch):
        """Test saving raw pages with override flag."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = ConcreteScraper("https://example.com")
        scraper.save_raw_pages("test content", override=True)
        raw_dir = scraper.SCRAPER_RAW_DATA
        assert raw_dir.exists()
        # Check that a file was created
        files = list(raw_dir.rglob("*.gz"))
        assert len(files) > 0

    def test_save_raw_pages_without_override(self, tmp_path, monkeypatch):
        """Test that raw pages are not saved without override when SAVE_RAW_PAGES is False."""
        # Use a unique path for this test to avoid interference from other tests
        test_raw_path = tmp_path / "raw_no_override"
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(test_raw_path))
        monkeypatch.setenv("SAVE_RAW_PAGES", "False")
        monkeypatch.setenv("DRY_RUN", "False")  # Not a dry run, but SAVE_RAW_PAGES is False
        # Clean up any existing files
        if test_raw_path.exists():
            import shutil
            shutil.rmtree(test_raw_path)
        scraper = ConcreteScraper("https://example.com")
        # Count files before calling save_raw_pages (should be 0)
        initial_files = []
        if scraper.SCRAPER_RAW_DATA.exists():
            initial_files = list(scraper.SCRAPER_RAW_DATA.rglob("*.gz"))
        initial_count = len(initial_files)
        scraper.save_raw_pages("test content", override=False)
        # Count files after calling save_raw_pages
        final_files = []
        if scraper.SCRAPER_RAW_DATA.exists():
            final_files = list(scraper.SCRAPER_RAW_DATA.rglob("*.gz"))
        final_count = len(final_files)
        # No new files should have been created (count should be the same)
        assert final_count == initial_count, f"Expected {initial_count} files, found {final_count}"


class TestScraperIntegration:
    """Integration tests for Scraper with real URLs."""

    @pytest.mark.integration
    def test_scraper_integration_httpbin_get(self, tmp_path, monkeypatch):
        """Integration test: Scrape httpbin.org/get endpoint."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        monkeypatch.setenv("SCRAPER_MAX_RETRIES", "1")
        monkeypatch.setenv("SCRAPER_TIMEOUT", "10")

        class HttpbinScraper(ConcreteScraper):
            def request(self, url, **kwargs):
                import requests
                return requests.get(url, timeout=10, verify=False)

        scraper = HttpbinScraper("https://httpbin.org/get")
        # The scrape method doesn't return a value, it just processes
        scraper.scrape()
        assert scraper.scrape_end_time is not None

