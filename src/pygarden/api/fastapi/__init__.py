"""Initialize the api/fastapi module."""
import importlib.util
import warnings

OPTIONAL_MODULES = [
    "psycopg",
    "pymssql",
    "requests",
    "redis",
    "celery",
    "fastapi"
]

for module_name in OPTIONAL_MODULES:
    if importlib.util.find_spec(module_name) is None:
        warnings.warn(
            f'You should install the extra "fastapi-api", missing required module: {module_name}.',
            UserWarning,
        )
    else:
        importlib.import_module(module_name)
