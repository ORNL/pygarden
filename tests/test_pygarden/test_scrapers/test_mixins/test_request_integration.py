"""Integration tests for RequestMixin with real URLs."""

import pytest

from pygarden.scrapers.mixins.request import RequestMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithRequestIntegration(RequestMixin, Scraper):
    """Test scraper using RequestMixin for integration tests."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": str(data.text) if hasattr(data, "text") else str(data)}


class TestRequestMixinIntegration:
    """Integration test cases for the RequestMixin with real URLs."""

    @pytest.mark.integration
    def test_request_mixin_integration_httpbin_get(self, tmp_path, monkeypatch):
        """Integration test: Request from httpbin.org/get."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithRequestIntegration("https://httpbin.org/get")
        try:
            result = scraper.request("https://httpbin.org/get", method="GET", timeout=10)
            assert result is not None
            assert hasattr(result, "status_code")
            # Accept 200 or skip if service unavailable (503)
            if result.status_code == 503:
                pytest.skip("Service unavailable (503)")
            assert result.status_code == 200
        except Exception as e:
            # Skip test if service is unavailable (503, timeout, connection errors)
            error_str = str(e)
            error_class = e.__class__.__name__
            if ("503" in error_str or 
                "Connection" in error_class or 
                "Timeout" in error_class or 
                "ReadTimeout" in error_class or
                "timeout" in error_str.lower()):
                pytest.skip(f"Service unavailable or timeout: {e}")
            raise

    @pytest.mark.integration
    def test_request_mixin_integration_httpbin_post(self, tmp_path, monkeypatch):
        """Integration test: POST request to httpbin.org/post."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithRequestIntegration("https://httpbin.org/post")
        try:
            result = scraper.request("https://httpbin.org/post", method="POST", json={"test": "data"}, timeout=10)
            assert result is not None
            assert hasattr(result, "status_code")
            # Accept 200 or skip if service unavailable (503)
            if result.status_code == 503:
                pytest.skip("Service unavailable (503)")
            assert result.status_code == 200
        except Exception as e:
            # Skip test if service is unavailable (503, timeout, connection errors)
            error_str = str(e)
            error_class = e.__class__.__name__
            if ("503" in error_str or 
                "Connection" in error_class or 
                "Timeout" in error_class or 
                "ReadTimeout" in error_class or
                "timeout" in error_str.lower()):
                pytest.skip(f"Service unavailable or timeout: {e}")
            raise

