#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module defines custom exception classes for various application components. Each exception class validates
specific error codes from 'ErrorCodes'. Included are 'ScraperException', 'DatabaseException', 'TemplateException', and 'ParserError',
each tailored to a specific component and type of error within the application.
"""
from typing import Optional

from pygarden.error_codes import ErrorCodes


class CommonException(Exception):
    def __init__(self, message=None, code=None):
        self.code = code if code else ErrorCodes.DEFAULT_ERROR
        self.validate_code(self.code)
        self.message = str(message)
        super().__init__(message)

    def __str__(self):
        return f"{self.message} (Error Code: {self.code})"

    @staticmethod
    def validate_code(code: Optional[int] = None):
        if code and not any(value == code for value in vars(ErrorCodes).values()):
            raise ValueError(f"Invalid error code: {code}")

    def __repr__(self):
        return f"{self.__class__.__name__}(message={self.args[0]!r}, code={self.code})"


class ScraperException(CommonException):
    @staticmethod
    def validate_code(code: Optional[int] = None):
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("SCRAPE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid scraper error code: {code}")


class DatabaseException(CommonException):
    @staticmethod
    def validate_code(code: Optional[int] = None):
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("DB_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid database error code: {code}")


class TemplateException(CommonException):
    @staticmethod
    def validate_code(code: Optional[int] = None):
        db_codes = {
            value for name, value in vars(ErrorCodes).items() if name.startswith("TEMPLATE_")
        }
        if code and code not in db_codes:
            raise ValueError(f"Invalid template error code: {code}")


class ParserError(ScraperException):
    def __init__(self, message=None):
        super().__init__(message, 2003)
