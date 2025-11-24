"""Initialize the api/flask module."""
import importlib.util
import warnings

OPTIONAL_MODULES = [
    "psycopg",
    "requests",
    "redis",
    "flask"
]

for module_name in OPTIONAL_MODULES:
    if importlib.util.find_spec(module_name) is None:
        warnings.warn(
            f'You should install the extra "flask-api", missing required module: {module_name}.',
            UserWarning,
        )
    else:
        importlib.import_module(module_name)