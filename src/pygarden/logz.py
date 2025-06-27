"""
Provide a standard logger for all use cases.

This module provides utilities for creating and configuring loggers with
different backends (Rich, Loguru, and standard Python logging). It supports
both console and file output with configurable formatting and log levels.

The module provides functions for:
- Creating logging handlers with file and console output
- Setting up Rich loggers with enhanced formatting and syntax highlighting
- Setting up Loguru loggers with better exception handling
- Setting up standard Python loggers
- A unified logger creation function with backend selection

Examples
--------
Create a Rich logger::

    >>> logger = create_rich_logger()
    >>> logger.info("Application started")

Create a logger with file output::

    >>> logger = create_logger(file_out="app.log", mode="a", encoding="utf-8")

Create a Loguru logger::

    >>> logger = create_loguru_logger(file_out="app.log")

Create a standard Python logger::

    >>> logger = create_python_logger(file_out="app.log")

Notes
-----
Environment Variables:
    - LOGLEVEL: Set the logging level (default: INFO)
    - LOGGER_TYPE: Set the default logger type (rich, loguru, logging)

Dependencies:
    - Rich: For enhanced console output and syntax highlighting
    - Loguru: For better exception handling and formatting
"""

import logging
import os
import sys


def create_handler(file_out, mode, encoding, another_handler=None):
    """
    Create a logging handler.

    This function creates a logging handler to format text written by the Python
    logging module. It can create file handlers and combine them with other
    handlers like console handlers.

    :param file_out: Path to file to output logs to
    :type file_out: str or None
    :param mode: Mode to open the file with (e.g., 'a', 'w')
    :type mode: str or None
    :param encoding: Encoding to open the file with
    :type encoding: str or None
    :param another_handler: Handler from another logging module to combine with file handler
    :type another_handler: logging.Handler or None
    :return: A tuple containing (file_handler, handlers) where file_handler is the
             created file handler (or None) and handlers is a list of all handlers
    :rtype: tuple

    Examples
    --------
    Create a file handler::

        >>> file_handler, handlers = create_handler("app.log", "a", "utf-8")

    Create a file handler with console handler::

        >>> console_handler = logging.StreamHandler()
        >>> file_handler, handlers = create_handler("app.log", "a", "utf-8", console_handler)

    Create handlers without file output::

        >>> file_handler, handlers = create_handler(None, None, None)
        >>> print(file_handler, handlers)
        None []
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
    Create a Rich logger.

    Creates a Rich logger for all uses with enhanced formatting, syntax
    highlighting, and traceback support. Rich provides beautiful console
    output with colors and better formatting.

    :param file_out: Path to file to output logs to
    :type file_out: str or None
    :param mode: Mode to open the file with
    :type mode: str or None
    :param encoding: Encoding to open the file with
    :type encoding: str or None
    :return: A Rich logger instance
    :rtype: logging.Logger
    :raises ImportError: If the rich package is not installed

    Examples
    --------
    Create a basic Rich logger::

        >>> logger = create_rich_logger()

    Create a Rich logger with file output::

        >>> logger = create_rich_logger("app.log", "a", "utf-8")

    Notes
    -----
    - Requires the 'rich' package to be installed
    - Automatically installs rich traceback handling
    - Uses environment variable LOGLEVEL for log level (default: INFO)
    - Provides enhanced formatting with colors and syntax highlighting
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
        datefmt="[%Y/%m/%d %H:%M;%S]",
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

    Creates a Loguru logger for all uses with enhanced formatting and
    better exception handling. Loguru provides better exception formatting
    and more intuitive API.

    :param file_out: Path to file to output logs to
    :type file_out: str or None
    :param mode: Mode to open the file with
    :type mode: str or None
    :param encoding: Encoding to open the file with
    :type encoding: str or None
    :return: A Loguru logger instance, or None if Loguru is not available
    :rtype: loguru.Logger or None

    Examples
    --------
    Create a basic Loguru logger::

        >>> logger = create_loguru_logger()

    Create a Loguru logger with file output::

        >>> logger = create_loguru_logger("app.log", "a", "utf-8")

    Notes
    -----
    - Requires the 'loguru' package to be installed
    - Uses environment variable LOGLEVEL for log level (default: INFO)
    - Provides better exception formatting and traceback handling
    - Returns None if Loguru is not available (graceful fallback)
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

    Creates a standard Python logger with both console and optional file output.
    This is the most basic logger type that doesn't require additional dependencies.

    :param file_out: Path to file to output logs to
    :type file_out: str or None
    :param mode: Mode to open the file with
    :type mode: str or None
    :param encoding: Encoding to open the file with
    :type encoding: str or None
    :return: Python logger instance
    :rtype: logging.Logger

    Examples
    --------
    Create a basic Python logger::

        >>> logger = create_python_logger()

    Create a Python logger with file output::

        >>> logger = create_python_logger("app.log", "a", "utf-8")

    Notes
    -----
    - Uses standard Python logging module (no additional dependencies)
    - Uses environment variable LOGLEVEL for log level (default: INFO)
    - Provides both console and file output when file_out is specified
    - Uses standard formatting with timestamps and log levels
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
            datefmt="[%Y/%m/%d %H:%M;%S]",
            handlers=handlers,
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s" + "%(levelname)8s - " + " - %(message)s",
            datefmt="[%Y/%m/%d %H:%M;%S]",
        )
    # if there is a file_handler set, close it before leaving :)
    # This prevents leaving open files
    if file_handler is not None:
        file_handler.close()
    return logging.getLogger()


def create_logger(file_out=None, mode=None, encoding=None, logger_type="rich"):
    """
    Create a logger instance.

    Creates a logger for all uses with support for different logger backends.
    The logger type can be specified via the LOGGER_TYPE environment variable
    or the logger_type parameter. This is the main entry point for logger creation.

    :param file_out: Path to file to output logs to
    :type file_out: str or None
    :param mode: Mode to open the file with
    :type mode: str or None
    :param encoding: Encoding to open the file with
    :type encoding: str or None
    :param logger_type: Logger to use for logging purpose
    :type logger_type: str
    :return: The logger that was created
    :rtype: logging.Logger or loguru.Logger

    Examples
    --------
    Create a Rich logger (default)::

        >>> logger = create_logger()

    Create a Loguru logger::

        >>> logger = create_logger(logger_type="loguru")

    Create a standard Python logger::

        >>> logger = create_logger(logger_type="logging")

    Create a logger with file output::

        >>> logger = create_logger("app.log", "a", "utf-8", "rich")

    Notes
    -----
    - Default logger type is 'rich' for enhanced console output
    - Falls back to 'logging' if 'rich' is not available
    - Uses environment variable LOGGER_TYPE if set
    - Removes any existing handlers from the root logger before creating new ones
    - Default mode is 'a' (append) and encoding is 'utf-8'
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
