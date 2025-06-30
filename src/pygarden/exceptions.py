"""
Provides custom exception classes for pygarden's modules.

The 'CommonError' class serves as the base class for all exceptions, providing a consistent interface and error code
validation. The 'ScraperError', 'DatabaseError', and 'TemplateError' classes inherit from 'CommonError' and implement
their own error code validation methods to ensure that the error codes used are appropriate for their respective
contexts.

**Usage Example:**
    >>> from pygarden.exceptions import ScraperError
    >>> raise ScraperError('Failed to scrape data', 2001)
"""
from typing import Optional

from pygarden.error_codes import ErrorCodes


class CommonError(Exception):
    """
    Base class for all exceptions in the application.

    This class provides a consistent interface for error handling with
    message and error code validation. All custom exceptions in pygarden
    should inherit from this class.

    **Attributes:**
        code (int): The error code associated with this exception.
        message (str): The error message.

    **Usage Notes:**
        - Always provide an error code when creating exceptions.
        - Error codes are validated against ErrorCodes class.
        - Use this as the base class for all custom exceptions.

    **Example:**
        >>> raise CommonError('Something went wrong', 9999)
    """

    def __init__(self, message=None, code=None):
        """
        Initialize the exception with a message and an error code.

        :param message: The error message (optional).
        :type message: str, optional
        :param code: The error code (optional, defaults to DEFAULT_ERROR).
        :type code: int, optional
        :raises ValueError: If the error code is not valid.
        """
        self.code = code if code else ErrorCodes.DEFAULT_ERROR
        self.validate_code(self.code)
        self.message = str(message)
        super().__init__(message)

    def __str__(self):
        """
        Return a string representation of the exception.

        :return: A formatted string with the message and error code.
        :rtype: str
        :example:
            >>> str(CommonError('Database failed', 1001))
            'Database failed (Error Code: 1001)'
        """
        return f"{self.message} (Error Code: {self.code})"

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code against the defined error codes.

        :param code: The error code to validate (optional).
        :type code: int, optional
        :raises ValueError: If the error code is not valid.
        :example:
            >>> CommonError.validate_code(1001)
            >>> CommonError.validate_code(99999)
            ValueError: Invalid error code: 99999
        """
        if code and not any(value == code for value in vars(ErrorCodes).values()):
            raise ValueError(f"Invalid error code: {code}")

    def __repr__(self):
        """
        Return a string representation of the exception.

        :return: A string representation suitable for debugging.
        :rtype: str
        :example:
            >>> repr(CommonError('Test error', 1001))
            "CommonError(message='Test error', code=1001)"
        """
        return f"{self.__class__.__name__}(message={self.args[0]!r}, code={self.code})"


class ScraperError(CommonError):
    """
    Exception raised for scraper errors in the application.

    This exception is used for errors that occur during web scraping operations.
    It validates that error codes are appropriate for scraping operations.

    **Usage Notes:**
        - Use error codes starting with 2000 (SCRAPE_* codes).
        - Common scraping errors include connection failures, timeouts, and parsing issues.

    **Example:**
        >>> raise ScraperError('Connection failed', 2001)
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for scraper errors.

        :param code: The error code to validate (optional).
        :type code: int, optional
        :raises ValueError: If the error code is not a valid scraper error code.
        :example:
            >>> ScraperError.validate_code(2001)
            >>> ScraperError.validate_code(1001)
            ValueError: Invalid scraper error code: 1001
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("SCRAPE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid scraper error code: {code}")


class DatabaseError(CommonError):
    """
    Exception raised for database errors in the scraper module.

    This exception is used for errors that occur during database operations.
    It validates that error codes are appropriate for database operations.

    **Usage Notes:**
        - Use error codes starting with 1000 (DB_* codes).
        - Common database errors include connection failures, timeouts, and integrity issues.

    **Example:**
        >>> raise DatabaseError('Connection failed', 1001)
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for database errors.

        :param code: The error code to validate (optional).
        :type code: int, optional
        :raises ValueError: If the error code is not a valid database error code.
        :example:
            >>> DatabaseError.validate_code(1001)
            >>> DatabaseError.validate_code(2001)
            ValueError: Invalid database error code: 2001
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("DB_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid database error code: {code}")


class TemplateError(CommonError):
    """
    Exception raised for template errors in the scraper module.

    This exception is used for errors that occur during template processing.
    It validates that error codes are appropriate for template operations.

    **Usage Notes:**
        - Use error codes starting with 3000 (TEMPLATE_* codes).
        - Common template errors include rendering failures, missing templates, and syntax errors.

    **Example:**
        >>> raise TemplateError('Template not found', 3002)
    """

    @staticmethod
    def validate_code(code: Optional[int] = None):
        """
        Validate the error code for template errors.

        :param code: The error code to validate (optional).
        :type code: int, optional
        :raises ValueError: If the error code is not a valid template error code.
        :example:
            >>> TemplateError.validate_code(3001)
            >>> TemplateError.validate_code(1001)
            ValueError: Invalid template error code: 1001
        """
        db_codes = {value for name, value in vars(ErrorCodes).items() if name.startswith("TEMPLATE_")}
        if code and code not in db_codes:
            raise ValueError(f"Invalid template error code: {code}")


class ParserError(ScraperError):
    """
    Exception raised for parser errors in the scraper module.

    This exception is used for errors that occur during HTML/XML parsing operations.
    It automatically uses the SCRAPE_PARSING_FAILED error code (2003).

    **Usage Notes:**
        - Automatically uses error code 2003 (SCRAPE_PARSING_FAILED).
        - Use this for HTML/XML parsing failures, malformed content, etc.

    **Example:**
        >>> raise ParserError('Failed to parse HTML')
    """

    def __init__(self, message=None):
        """
        Initialize the ParserError with a message and a specific error code.

        :param message: The error message (optional).
        :type message: str, optional
        :note:
            Automatically uses error code 2003 (SCRAPE_PARSING_FAILED).
        """
        super().__init__(message, 2003)
