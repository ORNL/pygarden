#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide error codes for pygarden.

This module defines a data class 'ErrorCodes' that instantiates various error codes used throughout the application.
It categorizes error codes into distinct sections for database operations, scraping processes,
templating issues, and provides a default error code for general use. Each error type is associated with specific
integer values, making it easier to manage and identify errors consistently across different components of the
application.

**Usage Example:**
    >>> from pygarden.error_codes import ErrorCodes
    >>> ErrorCodes.DB_CONNECTION_FAILED
    1001
"""
from dataclasses import dataclass


@dataclass
class ErrorCodes:
    """
    Data class to define error codes for pygarden operations.

    This class contains categorized error codes for different types of operations
    including database, scraping, and templating errors. Use these codes to
    standardize error handling and reporting throughout the application.

    **Attributes:**
        DB_CONNECTION_FAILED (int): Database connection failure error code.
        DB_TIMEOUT (int): Database timeout error code.
        DB_INTEGRITY_ERROR (int): Database integrity error code.
        SCRAPE_CONNECTION_ERROR (int): Web scraping connection error code.
        SCRAPE_TIMEOUT (int): Web scraping timeout error code.
        SCRAPE_PARSING_FAILED (int): Web scraping parsing failure error code.
        SCRAPE_DATA_NOT_FOUND (int): Web scraping data not found error code.
        TEMPLATE_RENDERING_FAILED (int): Template rendering failure error code.
        TEMPLATE_NOT_FOUND (int): Template not found error code.
        TEMPLATE_SYNTAX_ERROR (int): Template syntax error code.
        DEFAULT_ERROR (int): Catch-all error code for unspecified errors.

    **Usage Notes:**
        - Use these codes in custom exceptions and error handling logic.
        - Codes are grouped by operation type for clarity.
        - Extend this class if new error categories are needed.

    **Example:**
        >>> try:
        ...     raise Exception('Database failed', ErrorCodes.DB_CONNECTION_FAILED)
        ... except Exception as e:
        ...     print(e)
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
