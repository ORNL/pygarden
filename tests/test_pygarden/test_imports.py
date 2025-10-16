import importlib
import pkgutil


def iter_modules(package_name: str):
    pkg = importlib.import_module(package_name)
    for mod in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        yield mod.name


def test_all_modules_importable():
    # Import all submodules to ensure there are no import-time errors
    failures = []
    optional_modules = {
        "pygarden.llama_cpp",  # requires llama-cpp-python
        "pygarden.mixins.postgres",  # requires psycopg
        "pygarden.mixins.postgres_logger",  # requires psycopg
        "pygarden.mixins.minio_mixin",  # requires minio
        "pygarden.mixins.pandas_mixin",  # requires pandas and sqlalchemy
        "pygarden.mixins.multiple",  # requires psycopg, pymssql, etc.
        "pygarden.mixins.mssql",  # requires pymssql
        "pygarden.mixins.influx",  # requires influxdb-client
        "pygarden.scrapers.mixins.websocket",  # requires websockets
        "pygarden.scrapers.seleniumscraper",  # requires selenium
        "pygarden.scrpaers.webdriver",  # requires selenium
    }

    for name in iter_modules("pygarden"):
        if name in optional_modules:
            continue  # Skip optional modules that may not be installed
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, repr(exc)))
    assert not failures, f"Import failures: {failures}"
