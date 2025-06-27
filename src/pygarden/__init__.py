#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyGARDEN (General Application Resource Development Environment Network).

A comprehensive Python package that provides tools and utilities to assist in the
development of Python packages. It is designed to help developers create, test, 
and deploy their packages more efficiently.

The package includes:
- Database connectivity and management with multiple backend support
- Logging utilities with rich formatting and multiple output options
- Environment variable management and configuration
- File operations and data generation utilities
- Web scraping capabilities with Selenium and requests support
- Authentication methods including LDAP integration
- Email sending functionality
- Command-line interface tools

Examples
--------
Basic database usage::

    >>> from pygarden.mixins.postgres import PostgresMixin
    >>> from pygarden.database import Database
    >>> 
    >>> class MyDatabase(PostgresMixin, Database):
    ...     pass
    >>> 
    >>> with MyDatabase() as db:
    ...     results = db.query("SELECT NOW()")

Logging setup::

    >>> from pygarden.logz import create_logger
    >>> logger = create_logger()
    >>> logger.info("Application started")

Environment variable checking::

    >>> from pygarden.env import check_environment
    >>> db_host = check_environment("DATABASE_HOST", "localhost")

Web scraping with Selenium::

    >>> from pygarden.scrapers import SeleniumScraper
    >>> 
    >>> class MyScraper(SeleniumScraper):
    ...     def interact(self, web_driver):
    ...         return web_driver.page_source
    ...     def parse(self, data):
    ...         return data.find('title').text

File operations::

    >>> from pygarden.file_operations import write_file, read_file
    >>> write_file("test.txt", "Hello World")
    >>> content = read_file("test.txt")

Authentication::

    >>> from pygarden.auth import authenticate_ldap_user
    >>> user = authenticate_ldap_user("username", "password")

Email sending::

    >>> from pygarden.mail import send_email
    >>> send_email("Test Subject", "Test message")

Notes
-----
This package requires various optional dependencies depending on the features used:

- Database operations: psycopg2, sqlite3
- Web scraping: selenium, beautifulsoup4, requests
- Authentication: ldap3
- Logging: rich, loguru
- CLI: click

Version
-------
Current version: 0.3.22
"""
VERSION = "0.3.22"
