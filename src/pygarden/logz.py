"""Provide a standard logger for all use cases."""

import logging
import os
import sys


def create_handler(file_out, mode, encoding, another_handler=None):
    """
    Create a logging handler.

    create_handler:
        Creates a logging handler to format text written by Python logging module.

    :param file_out: Path to file to output logs to, defaults to None
    :type file_out: str, optional
    :param mode: Mode to open the file with, defaults to None
    :type mode: str, optional
    :param encoding: Encoding to open the file with, defaults to None
    :type encoding: str, optional
    :param another_handler: Handler from another logging module, defaults to None
    :type another_handler: handler, optional
    :return: A Python logging handler
    :rtype: handler
    """
    if file_out is not None:
        file_handler = logging.FileHandler(file_out, mode, encoding)
        file_handler_fmt = logging.Formatter("[%(asctime)s]" + "%(levelname)8s - " + " - %(message)s")
        file_handler.setFormatter(file_handler_fmt)
        handlers = [file_handler]
        if another_handler:
            handlers = [another_handler, file_handler]
    else:
        file_handler = None
        if another_handler:
            handlers = [another_handler]
        else:
            handlers = []

    return file_handler, handlers


def create_rich_logger(file_out=None, mode=None, encoding=None):
    """
    Create a rich logger.

    create_rich_logger:
        Creates a Rich logger for all uses

    :param file_out: Path to file to output logs to, defaults to None
    :type file_out: str, optional
    :param mode: Mode to open the file with, defaults to None
    :type mode: str, optional
    :param encoding: Encoding to open the file with, defaults to None
    :type encoding: str, optional
    :return: A Rich logger instance
    :rtype: Logger
    """
    try:
        from rich.logging import RichHandler
        from rich.traceback import install
    except ImportError:
        raise ImportError("Failed to load rich logger")

    install()
    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    file_handler, handlers = create_handler(file_out, mode, encoding, rich_handler)
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%Y/%m/%d %H:%M:%S]",
        handlers=handlers,
    )
    # if there is a file_handler set, close it before leaving :)
    # This prevents leaving open files
    if file_handler is not None:
        file_handler.close()
    rich_handler.close()
    return logging.getLogger("rich")


def create_loguru_logger(file_out=None, mode=None, encoding=None):
    """
    Create a loguru logger.

    create_loguru_logger:
        Creates a `loguru` logger for all uses

    :param file_out: Path to file to output logs to, defaults to None
    :type file_out: str, optional
    :param mode: Mode to open the file with, defaults to None
    :type mode: str, optional
    :param encoding: Encoding to open the file with, defaults to None
    :type encoding: str, optional
    :return: A Loguru logger instance
    :rtype: Logger
    """
    try:
        from loguru import logger as loguru_logger
    except Exception as e:
        print(f"Failed to load loguru logger: {e}")
        return

    loguru_logger.remove()
    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    if file_out is not None:
        loguru_logger.add(
            file_out,
            mode=mode,
            encoding=encoding,
            level=log_level,
            format="[{time:YYYY/MM/DD HH:mm:ss}] - {level} - {message}",
            backtrace=True,
            diagnose=True,
        )
    else:
        loguru_logger.add(
            sys.stderr,
            level=log_level,
            format="[{time:YYYY/MM/DD HH:mm:ss}] - {level} - {message}",
            backtrace=True,
            diagnose=True,
        )
    return loguru_logger


def create_python_logger(file_out=None, mode=None, encoding=None):
    """
    Create a Python logger for all uses.

    create_python_logger:
        Creates a Python logger for all uses

    :param file_out: Path to file to output logs to, defaults to None
    :type file_out: str, optional
    :param mode: Mode to open the file with, defaults to None
    :type mode: str, optional
    :param encoding: Encoding to open the file with, defaults to None
    :type encoding: str, optional
    :return: Python logger instance
    :rtype: Logger
    """
    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    file_handler, handlers = create_handler(file_out, mode, encoding)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler_fmt = logging.Formatter("[%(asctime)s]" + "%(levelname)8s - " + " - %(message)s")
    stdout_handler.setFormatter(stdout_handler_fmt)
    handlers.append(stdout_handler)
    if file_handler:
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%Y/%m/%d %H:%M:%S]",
            handlers=handlers,
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s" + "%(levelname)8s - " + " - %(message)s",
            datefmt="[%Y/%m/%d %H:%M:%S]",
        )
    # if there is a file_handler set, close it before leaving :)
    # This prevents leaving open files
    if file_handler is not None:
        file_handler.close()
    return logging.getLogger()


def create_logger(file_out=None, mode=None, encoding=None, logger_type="rich"):
    """
    Create a logger instance.

    create_logger:
        Creates a logger for all uses

    :param file_out: Path to file to output logs to, defaults to None
    :type file_out: str, optional
    :param mode: Mode to open the file with, defaults to None
    :type mode: str, optional
    :param encoding: Encoding to open the file with, defaults to None
    :type encoding: str, optional
    :param logger_type: Logger to use for logging purpose, defaults to rich (rich (default), loguru, logging)
    :type logger_type: str, optional
    :return: The logger that was created
    :rtype: Logger
    """
    # Remove any handler's that may have been set in the logging root
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)

    logger_type = os.getenv("LOGGER_TYPE", None) or logger_type
    mode = mode or "a"
    encoding = encoding or "utf-8"

    if logger_type == "loguru":
        return create_loguru_logger(file_out, mode, encoding)
    elif logger_type == "logging":
        return create_python_logger(file_out, mode, encoding)

    return create_rich_logger(file_out, mode, encoding)
