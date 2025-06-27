"""
Provides custom exception classes for pygarden's modules.

The 'CommonError' class serves as the base class for all exceptions, providing a consistent interface and error code
validation. The 'ScraperError', 'DatabaseError', and 'TemplateError' classes inherit from 'CommonError' and implement
their own error code validation methods to ensure that the error codes used are appropriate for their respective
contexts.

The module provides:
- Base exception class with error code validation
- Specialized exception classes for different modules
- Error code validation to ensure proper error categorization
- Consistent error message formatting across the application

Examples
--------
Raise a database error::

    >>> raise DatabaseError("Connection failed", code=1001)

Raise a scraper error::

    >>> raise ScraperError("Timeout occurred", code=2002)

Raise a template error::

    >>> raise TemplateError("Template not found", code=3002)

Use with error codes::

    >>> from pygarden.error_codes import ErrorCodes
    >>> raise DatabaseError("Connection failed", code=ErrorCodes.DB_CONNECTION_FAILED)

Notes
-----
All exception classes inherit from CommonError and provide:
- Error code validation specific to their domain
- Consistent error message formatting
- Integration with the ErrorCodes class
"""
from typing import Optional

from pygarden.error_codes import ErrorCodes


class CommonError(Exception):
    """
    Base class for all exceptions in the application.

    This class provides a consistent interface for all exceptions in the
    pygarden application, including error code validation and standardized
    error message formatting.

    :param message: The error message
    :type message: str or None
    :param code: The error code
    :type code: int or None

    Attributes
    ----------
    code : int
        The error code associated with this exception
    message : str
        The error message

    Examples
    --------
    >>> raise CommonError("Something went wrong", code=9999)
    Traceback (most recent call last):
    ...
    CommonError: Something went wrong (Error Code: 9999)

    Create with default error code::

        >>> error = CommonError("Generic error")
        >>> print(error.code)
        9999

    Create with custom error code::

        >>> error = CommonError("Custom error", code=5000)
        >>> print(error.code)
        5000

    Notes
    -----
    This class serves as the foundation for all custom exceptions in the
    pygarden application. It ensures consistent error handling and provides
    a standardized way to include error codes with exception messages.
    """

    def __init__(self, message=None, code=None):
        """
        Initialize the exception with a message and an error code.

        :param message: The error message
        :type message: str or None
        :param code: The error code
        :type code: int or None
        """
        self.code = code if code else ErrorCodes.DEFAULT_ERROR
        self.validate_code(self.code)
        self.message = str(message)
        super().__init__(message)

    def __str__(self):
        """
        Return a string representation of the exception.

        :return: Formatted error message with error code
        :rtype: str
        """
        return f"{self.message} (Error Code: {self.code})"

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code against the defined error codes.

        :param code: The error code to validate
        :type code: int or None
        :raises ValueError: If the error code is not valid

        Examples
        --------
        >>> CommonError.validate_code(1001)  # Valid code
        >>> CommonError.validate_code(9999)  # Valid code
        >>> CommonError.validate_code(9998)  # Invalid code
        Traceback (most recent call last):
        ...
        ValueError: Invalid error code: 9998

        Notes
        -----
        This method checks if the provided error code exists in the
        ErrorCodes class. It's used to ensure that only valid error
        codes are used throughout the application.
        """
        if code and not any(value == code for value in vars(ErrorCodes).values()):
            raise ValueError(f"Invalid error code: {code}")

    def __repr__(self):
        """
        Return a string representation of the exception.

        :return: Detailed string representation of the exception
        :rtype: str
        """
        return f"{self.__class__.__name__}(message={self.args[0]!r}, code={self.code})"


class ScraperError(CommonError):
    """
    Exception raised for scraper errors in the application.

    This exception is used for all web scraping related errors and validates
    that only scraper-specific error codes are used.

    :param message: The error message
    :type message: str or None
    :param code: The error code (must be a scraper error code)
    :type code: int or None

    Examples
    --------
    >>> raise ScraperError("Connection timeout", code=2002)
    Traceback (most recent call last):
    ...
    ScraperError: Connection timeout (Error Code: 2002)

    Use with error codes::

        >>> from pygarden.error_codes import ErrorCodes
        >>> raise ScraperError("Parsing failed", code=ErrorCodes.SCRAPE_PARSING_FAILED)

    Notes
    -----
    This exception validates that only error codes in the 2000-2999 range
    (scraper-related errors) are used.
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for scraper errors.

        :param code: The error code to validate
        :type code: int or None
        :raises ValueError: If the error code is not a valid scraper error code

        Examples
        --------
        >>> ScraperError.validate_code(2001)  # Valid scraper code
        >>> ScraperError.validate_code(1001)  # Invalid (database code)
        Traceback (most recent call last):
        ...
        ValueError: Invalid scraper error code: 1001

        Notes
        -----
        This method ensures that only scraper-specific error codes
        (those starting with "SCRAPE_") are used with this exception.
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("SCRAPE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid scraper error code: {code}")


class DatabaseError(CommonError):
    """
    Exception raised for database errors in the application.

    This exception is used for all database related errors and validates
    that only database-specific error codes are used.

    :param message: The error message
    :type message: str or None
    :param code: The error code (must be a database error code)
    :type code: int or None

    Examples
    --------
    >>> raise DatabaseError("Connection failed", code=1001)
    Traceback (most recent call last):
    ...
    DatabaseError: Connection failed (Error Code: 1001)

    Use with error codes::

        >>> from pygarden.error_codes import ErrorCodes
        >>> raise DatabaseError("Timeout occurred", code=ErrorCodes.DB_TIMEOUT)

    Notes
    -----
    This exception validates that only error codes in the 1000-1999 range
    (database-related errors) are used.
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for database errors.

        :param code: The error code to validate
        :type code: int or None
        :raises ValueError: If the error code is not a valid database error code

        Examples
        --------
        >>> DatabaseError.validate_code(1001)  # Valid database code
        >>> DatabaseError.validate_code(2001)  # Invalid (scraper code)
        Traceback (most recent call last):
        ...
        ValueError: Invalid database error code: 2001

        Notes
        -----
        This method ensures that only database-specific error codes
        (those starting with "DB_") are used with this exception.
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("DB_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid database error code: {code}")


class TemplateError(CommonError):
    """
    Exception raised for template errors in the application.

    This exception is used for all template related errors and validates
    that only template-specific error codes are used.

    :param message: The error message
    :type message: str or None
    :param code: The error code (must be a template error code)
    :type code: int or None

    Examples
    --------
    >>> raise TemplateError("Template not found", code=3002)
    Traceback (most recent call last):
    ...
    TemplateError: Template not found (Error Code: 3002)

    Use with error codes::

        >>> from pygarden.error_codes import ErrorCodes
        >>> raise TemplateError("Rendering failed", code=ErrorCodes.TEMPLATE_RENDERING_FAILED)

    Notes
    -----
    This exception validates that only error codes in the 3000-3999 range
    (template-related errors) are used.
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for template errors.

        :param code: The error code to validate
        :type code: int or None
        :raises ValueError: If the error code is not a valid template error code

        Examples
        --------
        >>> TemplateError.validate_code(3001)  # Valid template code
        >>> TemplateError.validate_code(1001)  # Invalid (database code)
        Traceback (most recent call last):
        ...
        ValueError: Invalid template error code: 1001

        Notes
        -----
        This method ensures that only template-specific error codes
        (those starting with "TEMPLATE_") are used with this exception.
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("TEMPLATE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid template error code: {code}")


class ParserError(ScraperError):
    """
    Exception raised for parser errors in the scraper module.

    This is a specialized scraper error specifically for parsing-related
    issues, automatically using the SCRAPE_PARSING_FAILED error code.

    :param message: The error message
    :type message: str or None

    Examples
    --------
    >>> raise ParserError("Failed to parse HTML content")
    Traceback (most recent call last):
    ...
    ParserError: Failed to parse HTML content (Error Code: 2003)

    Use in parsing functions::

        >>> def parse_html(html_content):
        ...     if not html_content:
        ...         raise ParserError("Empty HTML content provided")
        ...     # parsing logic here

    Notes
    -----
    This exception automatically uses error code 2003 (SCRAPE_PARSING_FAILED)
    and is specifically designed for parsing-related errors in web scraping
    operations.
    """

    def __init__(self, message=None):
        """
        Initialize the ParserError with a message and a specific error code.

        :param message: The error message
        :type message: str or None
        """
        super().__init__(message, 2003)
