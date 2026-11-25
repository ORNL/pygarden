"""Check publication decisions without contacting PyPI."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

spec = importlib.util.spec_from_file_location(
    "check_pypi_version", Path(__file__).parents[1] / "scripts" / "check_pypi_version.py"
)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_existing_version_is_skipped():
    """A successful lookup skips publishing even if local source has changed."""
    with patch.object(check, "urlopen", return_value=MagicMock()) as request:
        assert check.needs_publish("pygarden", "0.3.36") is False
    request.assert_called_once_with("https://pypi.org/pypi/pygarden/0.3.36/json", timeout=30)


def test_missing_version_is_published():
    """Only a missing version permits a new upload."""
    with patch.object(check, "urlopen", side_effect=HTTPError("", 404, "Not Found", None, None)):
        assert check.needs_publish("pygarden", "0.3.37") is True


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("", 403, "Forbidden", None, None),
        HTTPError("", 503, "Unavailable", None, None),
        URLError("offline"),
    ],
)
def test_lookup_errors_fail_instead_of_publishing(error):
    """An authentication, network, or service failure cannot trigger publishing."""
    with patch.object(check, "urlopen", side_effect=error), pytest.raises(type(error)):
        check.needs_publish("pygarden", "0.3.37")
