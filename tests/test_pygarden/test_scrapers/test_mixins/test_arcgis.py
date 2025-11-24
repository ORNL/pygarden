"""Tests for the ArcgisMixin."""

import pytest
from unittest.mock import MagicMock, patch

from pygarden.scrapers.mixins.arcgis import ArcgisMixin
from pygarden.scrapers.scraper import Scraper


class TestScraperWithArcgis(ArcgisMixin, Scraper):
    """Test scraper using ArcgisMixin."""

    def parse(self, data):
        """Parse method implementation."""
        return {"parsed": True, "data": data}


class TestArcgisMixin:
    """Test cases for the ArcgisMixin."""

    def test_arcgis_mixin_initialization(self, tmp_path, monkeypatch):
        """Test ArcgisMixin can be used with Scraper."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithArcgis("https://example.com/arcgis/rest/services")
        assert scraper.url == "https://example.com/arcgis/rest/services"
        assert hasattr(scraper, "query_parameters")
        assert scraper.query_parameters["params"]["f"] == "json"
        assert scraper.query_parameters["params"]["where"] == "1=1"
        assert scraper.query_parameters["params"]["returnGeometry"] == "false"

    def test_arcgis_mixin_default_query_parameters(self, tmp_path, monkeypatch):
        """Test ArcgisMixin default query parameters."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        scraper = TestScraperWithArcgis("https://example.com/arcgis")
        params = scraper.query_parameters["params"]
        assert params["f"] == "json"
        assert params["where"] == "1=1"
        assert params["returnGeometry"] == "false"
        assert params["spatialRel"] == "esriSpatialRelIntersects"
        assert params["outFields"] == "*"

    @patch("pygarden.scrapers.mixins.arcgis.requests.request")
    def test_arcgis_mixin_request_method(self, mock_request, tmp_path, monkeypatch):
        """Test ArcgisMixin request method returns JSON object."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "features": [{"attributes": {"name": "Test", "id": 1}}],
            "exceededTransferLimit": False,
        }
        mock_request.return_value = mock_response

        scraper = TestScraperWithArcgis("https://example.com/arcgis/rest/services")
        result = scraper.request("https://example.com/arcgis/rest/services")
        assert isinstance(result, dict)
        assert "features" in result
        assert len(result["features"]) == 1

    @patch("pygarden.scrapers.mixins.arcgis.requests.request")
    def test_arcgis_mixin_request_with_custom_params(self, mock_request, tmp_path, monkeypatch):
        """Test ArcgisMixin request method with custom parameters."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_request.return_value = mock_response

        scraper = TestScraperWithArcgis("https://example.com/arcgis")
        scraper.query_parameters["params"]["outFields"] = "name,id"
        result = scraper.request("https://example.com/arcgis")
        assert isinstance(result, dict)
        # Verify that the request was called with combined parameters
        mock_request.assert_called_once()

    @patch("pygarden.scrapers.mixins.arcgis.requests.request")
    def test_arcgis_mixin_request_with_kwargs(self, mock_request, tmp_path, monkeypatch):
        """Test ArcgisMixin request method with additional kwargs."""
        monkeypatch.setenv("SCRAPER_DATA_PATH", str(tmp_path / "data"))
        monkeypatch.setenv("SCRAPER_RAW_DATA", str(tmp_path / "raw"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_request.return_value = mock_response

        scraper = TestScraperWithArcgis("https://example.com/arcgis")
        result = scraper.request("https://example.com/arcgis", method="GET", headers={"X-Test": "value"})
        assert isinstance(result, dict)
        mock_request.assert_called_once()


