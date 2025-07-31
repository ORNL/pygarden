"""Initialize the scrapers module."""

import importlib.util
import warnings

OPTIONAL_MODULES = [
    "bs4",
    "cfscrape",
    "cloudscraper",
    "requests",
    "selenium",
    "urllib3",
    "websocket",
]

for module_name in OPTIONAL_MODULES:
    if importlib.util.find_spec(module_name) is None:
        warnings.warn(
            f'You should install the extra "scrapers", missing required module: {module_name}.',
            UserWarning,
        )
    else:
        importlib.import_module(module_name)
