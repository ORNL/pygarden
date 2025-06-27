#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide error codes for pygarden.

This module defines a data class 'ErrorCodes' that instantiates various error codes used throughout the application.
It categorizes error codes into distinct sections for database operations, scraping processes,
templating issues, and provides a default error code for general use. Each error type is associated with specific
integer values, making it easier to manage and identify errors consistently across different components of the
application.

The module provides:
- Centralized error code definitions
- Categorized error codes by functionality
- Consistent error code numbering scheme
- Easy access to error codes throughout the application

Examples
--------
Access database error codes::

    >>> from pygarden.error_codes import ErrorCodes
    >>> ErrorCodes.DB_CONNECTION_FAILED
    1001

Access scraping error codes::

    >>> ErrorCodes.SCRAPE_TIMEOUT
    2002

Access templating error codes::

    >>> ErrorCodes.TEMPLATE_NOT_FOUND
    3002

Use error codes in exceptions::

    >>> from pygarden.exceptions import DatabaseError
    >>> raise DatabaseError("Connection failed", code=ErrorCodes.DB_CONNECTION_FAILED)

Notes
-----
Error Code Ranges:
    - 1000-1999: Database related errors
    - 2000-2999: Web scraping related errors
    - 3000-3999: Template related errors
    - 9999: Default/general error code
"""
from dataclasses import dataclass


@dataclass
class ErrorCodes:
    """
    A data class to define error codes.

    This class provides a centralized location for all error codes used
    throughout the pygarden application. Error codes are organized by
    category and follow a consistent numbering scheme.

    Attributes
    ----------
    DB_CONNECTION_FAILED : int
        Error code for database connection failures (1001)
    DB_TIMEOUT : int
        Error code for database timeout errors (1002)
    DB_INTEGRITY_ERROR : int
        Error code for database integrity violations (1003)
    SCRAPE_CONNECTION_ERROR : int
        Error code for web scraping connection errors (2001)
    SCRAPE_TIMEOUT : int
        Error code for web scraping timeout errors (2002)
    SCRAPE_PARSING_FAILED : int
        Error code for web scraping parsing failures (2003)
    SCRAPE_DATA_NOT_FOUND : int
        Error code for web scraping data not found errors (2004)
    TEMPLATE_RENDERING_FAILED : int
        Error code for template rendering failures (3001)
    TEMPLATE_NOT_FOUND : int
        Error code for template not found errors (3002)
    TEMPLATE_SYNTAX_ERROR : int
        Error code for template syntax errors (3003)
    DEFAULT_ERROR : int
        Default error code for general errors (9999)

    Examples
    --------
    >>> codes = ErrorCodes()
    >>> codes.DB_CONNECTION_FAILED
    1001
    >>> codes.SCRAPE_TIMEOUT
    2002
    >>> codes.TEMPLATE_NOT_FOUND
    3002
    >>> codes.DEFAULT_ERROR
    9999

    Use in exception handling::

        >>> try:
        ...     # Some database operation
        ...     pass
        ... except ConnectionError:
        ...     raise DatabaseError("Connection failed", code=ErrorCodes.DB_CONNECTION_FAILED)

    Notes
    -----
    This class uses Python's dataclass decorator for automatic generation
    of __init__, __repr__, and other special methods. All error codes
    are defined as class attributes for easy access throughout the application.
    """

    # Database Errors
    DB_CONNECTION_FAILED: int = 1001
    DB_TIMEOUT: int = 1002
    DB_INTEGRITY_ERROR: int = 1003

    # Web Scraping Errors
    SCRAPE_CONNECTION_ERROR: int = 2001
    SCRAPE_TIMEOUT: int = 2002
    SCRAPE_PARSING_FAILED: int = 2003
    SCRAPE_DATA_NOT_FOUND: int = 2004

    # Templating Errors
    TEMPLATE_RENDERING_FAILED: int = 3001
    TEMPLATE_NOT_FOUND: int = 3002
    TEMPLATE_SYNTAX_ERROR: int = 3003

    # Catch all Error
    DEFAULT_ERROR: int = 9999
