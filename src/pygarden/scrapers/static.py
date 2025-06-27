#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide static objects.

This module provides static data classes and configurations for various
utilities including color codes for terminal output, URL regex patterns,
and image processing configurations.

The module provides:
- Colors class with ANSI color codes for terminal output
- UrlRegex class with compiled regex patterns for URL validation
- ImageConfig class with configuration dictionaries for image processing

Examples
--------
Use color codes for terminal output::

    >>> print(f"{Colors.GREEN}Success{Colors.RESET}")

Check if a string matches URL pattern::

    >>> import re
    >>> url = "https://example.com"
    >>> bool(UrlRegex.HTTP.match(url))
    True

Use image configuration::

    >>> config = ImageConfig.PD
    >>> print(config['skipinitialspace'])
    True

Use colors in logging::

    >>> print(f"{Colors.RED}Error occurred{Colors.RESET}")
    >>> print(f"{Colors.YELLOW}Warning message{Colors.RESET}")

Validate different URL types::

    >>> ftp_url = "ftp://ftp.example.com/files/"
    >>> bool(UrlRegex.FTP.match(ftp_url))
    True
    >>> bool(UrlRegex.HTTP.match(ftp_url))
    False

Notes
-----
The Colors class provides ANSI escape sequences for terminal colorization.
The UrlRegex class contains pre-compiled regex patterns for efficient URL validation.
The ImageConfig class provides common configuration settings for image processing.
"""
import re
from dataclasses import dataclass


@dataclass
class Colors:
    """
    Provide a dataclass of colors for pretty printing.

    This class contains ANSI color codes for terminal output formatting.
    Each color is defined as an ANSI escape sequence that can be used
    to colorize text in terminal applications.

    Attributes
    ----------
    BLACK : str
        ANSI code for black text
    RED : str
        ANSI code for red text
    GREEN : str
        ANSI code for green text
    YELLOW : str
        ANSI code for yellow text
    BLUE : str
        ANSI code for blue text
    VIOLET : str
        ANSI code for violet text
    BEIGE : str
        ANSI code for beige text
    WHITE : str
        ANSI code for white text
    RESET : str
        ANSI code to reset text color to default

    Examples
    --------
    Print colored text::

        >>> print(f"{Colors.GREEN}Success!{Colors.RESET}")
        Success!  # (in green color)

    Print error message::

        >>> print(f"{Colors.RED}Error occurred{Colors.RESET}")
        Error occurred  # (in red color)

    Print warning message::

        >>> print(f"{Colors.YELLOW}Warning{Colors.RESET}")
        Warning  # (in yellow color)

    Create colored status messages::

        >>> status = "completed"
        >>> if status == "completed":
        ...     print(f"{Colors.GREEN}✓ {status}{Colors.RESET}")
        ... elif status == "error":
        ...     print(f"{Colors.RED}✗ {status}{Colors.RESET}")
        ... else:
        ...     print(f"{Colors.YELLOW}⚠ {status}{Colors.RESET}")

    Notes
    -----
    These ANSI color codes work in most modern terminals. The RESET code
    should be used after colored text to return to the default terminal color.
    """

    BLACK = "\33[30m"
    RED = "\33[31m"
    GREEN = "\33[32m"
    YELLOW = "\33[33m"
    BLUE = "\33[34m"
    VIOLET = "\33[35m"
    BEIGE = "\33[36m"
    WHITE = "\33[37m"
    RESET = "\33[39m"


@dataclass
class UrlRegex:
    """
    Define URL regex patterns.

    This class contains compiled regular expressions for matching different
    types of URLs including HTTP/HTTPS and FTP/SFTP protocols.

    Attributes
    ----------
    HTTP : re.Pattern
        Compiled regex pattern for HTTP and HTTPS URLs
    FTP : re.Pattern
        Compiled regex pattern for FTP and SFTP URLs

    Examples
    --------
    Match HTTP URLs::

        >>> url = "https://example.com/path?param=value"
        >>> bool(UrlRegex.HTTP.match(url))
        True

    Match FTP URLs::

        >>> ftp_url = "ftp://ftp.example.com/files/"
        >>> bool(UrlRegex.FTP.match(ftp_url))
        True

    Check invalid URL::

        >>> invalid_url = "not-a-url"
        >>> bool(UrlRegex.HTTP.match(invalid_url))
        False

    Validate different URL formats::

        >>> urls = [
        ...     "http://example.com",
        ...     "https://sub.example.com/path",
        ...     "ftp://ftp.example.com",
        ...     "sftp://server.example.com/files"
        ... ]
        >>> for url in urls:
        ...     if UrlRegex.HTTP.match(url):
        ...         print(f"{url} is HTTP/HTTPS")
        ...     elif UrlRegex.FTP.match(url):
        ...         print(f"{url} is FTP/SFTP")

    Notes
    -----
    These regex patterns are pre-compiled for efficiency. The HTTP pattern
    matches both HTTP and HTTPS URLs, while the FTP pattern matches both
    FTP and SFTP URLs.
    """

    # https://stackoverflow.com/a/48689681/2060081
    HTTP = re.compile(
        r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\." + r"([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
    )
    FTP = re.compile(
        r"((ftp|sftp)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\." + r"([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
    )


@dataclass
class ImageConfig:
    """
    Static dictionaries and values for OCR of images.

    This class contains configuration dictionaries for image processing
    and OCR (Optical Character Recognition) operations.

    Attributes
    ----------
    PD : dict
        Configuration dictionary for pandas data processing with common
        settings for handling CSV and image data

    Examples
    --------
    Use pandas configuration::

        >>> import pandas as pd
        >>> config = ImageConfig.PD
        >>> df = pd.read_csv("data.csv", **config)

    Check configuration values::

        >>> print(ImageConfig.PD['skipinitialspace'])
        True
        >>> print(ImageConfig.PD['na_values'])
        [' ', '  ', 'na', 'nan']

    Apply configuration to data processing::

        >>> config = ImageConfig.PD
        >>> df = pd.read_csv("data.csv", **config)
        >>> print(f"Loaded {len(df)} rows with {len(df.columns)} columns")

    Customize configuration::

        >>> config = ImageConfig.PD.copy()
        >>> config['thousands'] = '.'  # Use dot as thousands separator
        >>> config['decimal'] = ','    # Use comma as decimal separator
        >>> df = pd.read_csv("european_data.csv", **config)

    Notes
    -----
    The PD configuration provides sensible defaults for pandas data processing,
    including handling of missing values, date parsing, and number formatting.
    These settings are particularly useful for processing data extracted from
    images or OCR operations.
    """

    PD = {
        "skipinitialspace": True,
        "na_values": [" ", "  ", "na", "nan"],
        "keep_default_na": True,
        "skip_blank_lines": True,
        "parse_dates": True,
        "infer_datetime_format": True,
        "thousands": ",",
        "decimal": ".",
        "error_bad_lines": False,
        "warn_bad_lines": True,
    }
