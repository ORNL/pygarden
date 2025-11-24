"""Integration tests for HtmlMixin with real URLs."""

import pytest

from pygarden.scrapers.mixins.html import HtmlMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithHtmlIntegration(HtmlMixin, Scraper):
    """Test scraper using HtmlMixin for integration tests."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data)}


class TestHtmlMixinIntegration:
    """Integration test cases for the HtmlMixin with real URLs."""

    @pytest.mark.integration
    def test_html_mixin_integration_example_com(self, tmp_path, monkeypatch):
        """Integration test: Request HTML from example.com."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithHtmlIntegration("https://example.com")
        result = scraper.request("https://example.com", method="GET")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object
        # Example.com should have an h1 tag
        h1 = result.find("h1")
        assert h1 is not None

    @pytest.mark.integration
    def test_html_mixin_integration_httpbin_html(self, tmp_path, monkeypatch):
        """Integration test: Request HTML from httpbin.org/html."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithHtmlIntegration("https://httpbin.org/html")
        result = scraper.request("https://httpbin.org/html", method="GET")
        assert result is not None
        assert hasattr(result, "find")  # BeautifulSoup object


