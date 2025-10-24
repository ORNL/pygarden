#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide error codes for pygarden.

This module defines a data class 'ErrorCodes' that instantiates various error codes used throughout the application.
It categorizes error codes into distinct sections for database operations, scraping processes,
templating issues, and provides a default error code for general use. Each error type is associated with specific
integer values, making it easier to manage and identify errors consistently across different components of the
application.
"""

from dataclasses import dataclass


@dataclass
class ErrorCodes:
    """A data class to define error codes."""

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
