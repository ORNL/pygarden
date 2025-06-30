"""
Provide a standard logger for all use cases.

This module provides utility functions to create different types of loggers:
- Rich logger (default): Enhanced console output with colors and formatting
- Loguru logger: Advanced logging with better tracebacks and async support
- Python logger: Standard Python logging module

All loggers support file output and various configuration options.
Log level is controlled by the LOGLEVEL environment variable (default: INFO).

**Environment Variables:**
    LOGLEVEL: The logging level (default: INFO)
    LOGGER_TYPE: The type of logger to use (rich, loguru, logging)

**Usage Example:**
    >>> logger = create_logger('app.log', logger_type='rich')
    >>> logger.info('Application started')
"""

import logging
import os
import sys


def create_handler(file_out, mode, encoding, another_handler=None):
    """
    Create a logging handler for file output.

    Creates a logging handler to format text written by Python logging module.
    This function is used internally by other logger creation functions.

    :param file_out: Path to file to output logs to (default: None).
    :type file_out: str, optional
    :param mode: Mode to open the file with (default: None).
    :type mode: str, optional
    :param encoding: Encoding to open the file with (default: None).
    :type encoding: str, optional
    :param another_handler: Handler from another logging module (default: None).
    :type another_handler: logging.Handler, optional
    :return: A tuple containing (file_handler, handlers).
    :rtype: tuple
    :note:
        If file_out is None, no file handler is created.
        If another_handler is provided, it is included in the handlers list.
    :example:
        >>> file_handler, handlers = create_handler('app.log', 'a', 'utf-8')
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
    Create a rich logger with enhanced console output.

    Creates a Rich logger for all uses with colored output, better formatting,
    and enhanced tracebacks. This is the default logger type.

    :param file_out: Path to file to output logs to (default: None).
    :type file_out: str, optional
    :param mode: Mode to open the file with (default: None).
    :type mode: str, optional
    :param encoding: Encoding to open the file with (default: None).
    :type encoding: str, optional
    :return: A Rich logger instance.
    :rtype: logging.Logger
    :raises ImportError: If rich module is not available.
    :side effects: Installs rich traceback handler globally.
    :note:
        Requires the 'rich' package to be installed.
        Sets up rich tracebacks for better error reporting.
    :example:
        >>> logger = create_rich_logger('app.log')
        >>> logger.info('Rich logging enabled')
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
    Create a loguru logger with advanced features.

    Creates a Loguru logger for all uses with better tracebacks, async support,
    and more advanced configuration options.

    :param file_out: Path to file to output logs to (default: None).
    :type file_out: str, optional
    :param mode: Mode to open the file with (default: None).
    :type mode: str, optional
    :param encoding: Encoding to open the file with (default: None).
    :type encoding: str, optional
    :return: A Loguru logger instance or None if import fails.
    :rtype: loguru.Logger or None
    :note:
        Requires the 'loguru' package to be installed.
        If import fails, returns None instead of raising an exception.
        Removes default loguru handlers before configuration.
    :example:
        >>> logger = create_loguru_logger('app.log')
        >>> if logger:
        ...     logger.info('Loguru logging enabled')
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
    Create a standard Python logger.

    Creates a Python logger for all uses using the standard logging module.
    This is the most basic logger type with standard formatting.

    :param file_out: Path to file to output logs to (default: None).
    :type file_out: str, optional
    :param mode: Mode to open the file with (default: None).
    :type mode: str, optional
    :param encoding: Encoding to open the file with (default: None).
    :type encoding: str, optional
    :return: Python logger instance.
    :rtype: logging.Logger
    :side effects: Configures global logging settings.
    :note:
        Always adds a stdout handler for console output.
        Uses standard Python logging formatting.
    :example:
        >>> logger = create_python_logger('app.log')
        >>> logger.info('Standard logging enabled')
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
    Create a logger instance based on the specified type.

    Creates a logger for all uses. The type of logger is determined by the
    logger_type parameter or the LOGGER_TYPE environment variable.

    :param file_out: Path to file to output logs to (default: None).
    :type file_out: str, optional
    :param mode: Mode to open the file with (default: "a").
    :type mode: str, optional
    :param encoding: Encoding to open the file with (default: "utf-8").
    :type encoding: str, optional
    :param logger_type: Logger to use for logging purpose (default: "rich").
                        Options: "rich" (default), "loguru", "logging".
    :type logger_type: str, optional
    :return: The logger that was created.
    :rtype: logging.Logger or loguru.Logger
    :side effects: Removes existing root handlers and configures global logging.
    :note:
        The LOGGER_TYPE environment variable overrides the logger_type parameter.
        Default mode is "a" (append) and default encoding is "utf-8".
        Removes any existing handlers from the logging root before configuration.
    :example:
        >>> logger = create_logger('app.log', logger_type='rich')
        >>> logger = create_logger(logger_type='loguru')
        >>> logger = create_logger(logger_type='logging')
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
