"""Emit a GitHub Actions output indicating whether the project needs publishing."""

import tomllib
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen


def needs_publish(name: str, version: str) -> bool:
    """Publish only versions that PyPI reports as missing; propagate service errors."""
    url = f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(version, safe='')}/json"
    try:
        with urlopen(url, timeout=30):
            return False
    except HTTPError as error:
        if error.code == 404:
            return True
        raise


if __name__ == "__main__":
    with Path("pyproject.toml").open("rb") as source:
        project = tomllib.load(source)["project"]
    print(f"publish={str(needs_publish(project['name'], project['version'])).lower()}")
