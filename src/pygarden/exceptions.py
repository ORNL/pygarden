"""
Provides custom exception classes for pygarden's modules.

The 'CommonError' class serves as the base class for all exceptions, providing a consistent interface and error code
validation. The 'ScraperError', 'DatabaseError', and 'TemplateError' classes inherit from 'CommonError' and implement
their own error code validation methods to ensure that the error codes used are appropriate for their respective
contexts.
"""

from typing import Optional

from pygarden.error_codes import ErrorCodes


class CommonError(Exception):
    """Base class for all exceptions in the application."""

    def __init__(self, message=None, code=None):
        """Initialize the exception with a message and an error code."""
        self.code = code if code else ErrorCodes.DEFAULT_ERROR
        self.validate_code(self.code)
        self.message = str(message)
        super().__init__(message)

    def __str__(self):
        """Return a string representation of the exception."""
        return f"{self.message} (Error Code: {self.code})"

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """Validate the error code against the defined error codes."""
        if code and not any(value == code for value in vars(ErrorCodes).values()):
            raise ValueError(f"Invalid error code: {code}")

    def __repr__(self):
        """Return a string representation of the exception."""
        return f"{self.__class__.__name__}(message={self.args[0]!r}, code={self.code})"


class ScraperError(CommonError):
    """Exception raised for scraper errors in the application."""

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """Validate the error code for scraper errors."""
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("SCRAPE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid scraper error code: {code}")


class DatabaseError(CommonError):
    """Exception raised for database errors in the scraper module."""

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """Validate the error code for database errors."""
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("DB_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid database error code: {code}")


class TemplateError(CommonError):
    """Exception raised for template errors in the scraper module."""

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """Validate the error code for template errors."""
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("TEMPLATE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid template error code: {code}")


class ParserError(ScraperError):
    """Exception raised for parser errors in the scraper module."""

    def __init__(self, message=None):
        """Initialize the ParserError with a message and a specific error code."""
        super().__init__(message, 2003)
