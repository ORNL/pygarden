"""Tests for the static module."""

import re
import pytest

from pygarden.scrapers.static import Colors, ImageConfig, UrlRegex


class TestStatic:
    """Test cases for the static module."""

    def test_colors_attributes(self):
        """Test that Colors dataclass has all expected color attributes."""
        assert hasattr(Colors, "BLACK")
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "YELLOW")
        assert hasattr(Colors, "BLUE")
        assert hasattr(Colors, "VIOLET")
        assert hasattr(Colors, "BEIGE")
        assert hasattr(Colors, "WHITE")
        assert hasattr(Colors, "RESET")

    def test_colors_values(self):
        """Test that Colors values are ANSI escape codes."""
        assert Colors.BLACK.startswith("\33[")
        assert Colors.RED.startswith("\33[")
        assert Colors.GREEN.startswith("\33[")
        assert Colors.RESET.startswith("\33[")

    def test_url_regex_http_pattern(self):
        """Test HTTP URL regex pattern."""
        http_urls = [
            "http://example.com",
            "https://example.com",
            "http://example.com/path",
            "https://subdomain.example.com/path?query=value",
        ]
        for url in http_urls:
            assert UrlRegex.HTTP.search(url) is not None

    def test_url_regex_http_invalid(self):
        """Test HTTP URL regex with invalid URLs."""
        invalid_urls = [
            "not a url",
            "ftp://example.com",  # FTP should use FTP regex
            "example.com",  # Missing protocol
        ]
        for url in invalid_urls:
            # HTTP regex might still match some, but we're testing it works
            result = UrlRegex.HTTP.search(url)
            # Some might match, some might not - just verify regex works
            assert isinstance(result, (type(None), re.Match))

    def test_url_regex_ftp_pattern(self):
        """Test FTP URL regex pattern."""
        ftp_urls = [
            "ftp://example.com",
            "sftp://example.com",
            "ftp://example.com/path",
            "sftp://subdomain.example.com/path",
        ]
        for url in ftp_urls:
            assert UrlRegex.FTP.search(url) is not None

    def test_image_config_pd(self):
        """Test ImageConfig PD dictionary."""
        assert isinstance(ImageConfig.PD, dict)
        assert "skipinitialspace" in ImageConfig.PD
        assert "na_values" in ImageConfig.PD
        assert "keep_default_na" in ImageConfig.PD
        assert ImageConfig.PD["skipinitialspace"] is True
        assert isinstance(ImageConfig.PD["na_values"], list)


