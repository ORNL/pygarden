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
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            # Handle cases where module exists but fails to import due to dependency issues
            # (e.g., cfscrape/cloudscraper with urllib3 2.x)
            if "DEFAULT_CIPHERS" in str(e) or "urllib3" in str(e).lower():
                warnings.warn(
                    f'Module {module_name} is installed but incompatible with current urllib3 version. '
                    f'Error: {e}. Consider updating {module_name} or using urllib3<2.0.',
                    UserWarning,
                )
            else:
                # Re-raise if it's a different import error
                raise
