import importlib


def test_logz_create_logger():
    logz = importlib.import_module("pygarden.logz")
    logger = logz.create_logger()
    logger.info("hello")


def test_env_helpers():
    env = importlib.import_module("pygarden.env")
    assert callable(env.check_environment)


def test_error_codes_and_exceptions_import():
    importlib.import_module("pygarden.error_codes")
    importlib.import_module("pygarden.exceptions")


def test_cli_entry_point_import():
    # Ensure CLI module imports; not executing click commands here
    importlib.import_module("pygarden.cli")
