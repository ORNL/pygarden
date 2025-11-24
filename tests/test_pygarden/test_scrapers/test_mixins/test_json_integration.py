"""Integration tests for JsonMixin with real URLs."""

import pytest

from pygarden.scrapers.mixins.json import JsonMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithJsonIntegration(JsonMixin, Scraper):
    """Test scraper using JsonMixin for integration tests."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": data}


class TestJsonMixinIntegration:
    """Integration test cases for the JsonMixin with real URLs."""

    @pytest.mark.integration
    def test_json_mixin_integration_httpbin_json(self, tmp_path, monkeypatch):
        """Integration test: Request JSON from httpbin.org/json."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithJsonIntegration("https://httpbin.org/json")
        try:
            result = scraper.request("https://httpbin.org/json", method="GET", timeout=10)
            assert isinstance(result, dict)
            assert "slideshow" in result or "origin" in result or len(result) > 0
        except Exception as e:
            # Skip test if service is unavailable (503, connection errors, JSON decode errors, etc.)
            error_str = str(e)
            error_class = e.__class__.__name__
            if ("503" in error_str or 
                "Connection" in error_class or 
                "Timeout" in error_class or 
                "ReadTimeout" in error_class or
                "JSONDecodeError" in error_class or
                "timeout" in error_str.lower()):
                pytest.skip(f"Service unavailable or returned invalid response: {e}")
            raise

    @pytest.mark.integration
    def test_json_mixin_integration_httpbin_get(self, tmp_path, monkeypatch):
        """Integration test: Request JSON response from httpbin.org/get."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithJsonIntegration("https://httpbin.org/get")
        try:
            result = scraper.request("https://httpbin.org/get?test=value", method="GET", timeout=10)
            assert isinstance(result, dict)
            assert "url" in result or "args" in result
        except Exception as e:
            # Skip test if service is unavailable (503, connection errors, JSON decode errors, etc.)
            error_str = str(e)
            error_class = e.__class__.__name__
            if ("503" in error_str or 
                "Connection" in error_class or 
                "Timeout" in error_class or 
                "ReadTimeout" in error_class or
                "JSONDecodeError" in error_class or
                "timeout" in error_str.lower()):
                pytest.skip(f"Service unavailable or returned invalid response: {e}")
            raise

