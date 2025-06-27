#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide a base scraper class.

This module provides a base Scraper class that serves as the foundation for
all web scraping operations. It includes mixin classes for different data
formats (HTML, XML, JSON) and provides a unified interface for web scraping.

Examples
--------
Create a custom HTML scraper:
    >>> class MyScraper(Scraper, HTMLMixin):
    ...     def parse(self, data):
    ...         # Parse HTML data
    ...         soup = BeautifulSoup(data, 'html.parser')
    ...         return soup.find('title').text

Create a custom JSON scraper:
    >>> class ApiScraper(Scraper, JSONMixin):
    ...     def parse(self, data):
    ...         # Parse JSON data
    ...         return data['results']
"""
import collections.abc
import gzip
import re
import sys
import time
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import selenium.common.exceptions
import urllib3.exceptions

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

RE_DOMAIN = re.compile("https?://([A-Za-z_0-9.-]+).*")


__authors__ = ["grantjn@ornl.gov", "colletim@ornl.gov"]


class Scraper(ABC):
    """
    Base class for all scrapers.

    This abstract base class provides the foundation for web scraping
    operations. It handles URL management, request configuration, and
    provides a common interface for all scraper implementations.

    Parameters
    ----------
    url : str
        The URL to scrape
    **kwargs
        Optional keyword arguments for requests

    Attributes
    ----------
    url : str
        The URL being scraped
    request_args : dict
        Arguments for the request method
    logger : Logger
        Logger instance for this scraper

    Examples
    --------
    Create a custom scraper:
        >>> class MyScraper(Scraper, HTMLMixin):
        ...     def parse(self, data):
        ...         # Custom parsing logic
        ...         return data.find('title').text
        >>> 
        >>> scraper = MyScraper("https://example.com")
        >>> result = scraper.scrape()
    """

    # Is this a dry run?
    DRY_RUN = ce("DRY_RUN", False)
    # Do we write out the raw pages?
    SAVE_RAW_PAGES = ce("SAVE_RAW_PAGES", False)
    # How many times do we try connecting/getting data before giving up?
    SCRAPER_MAX_RETRIES = ce("SCRAPER_MAX_RETRIES", 3)
    # How long should we give a site to respond before giving up?
    SCRAPER_TIMEOUT = ce("SCRAPER_TIMEOUT", 60)
    # Path to save resulting data to
    SCRAPER_DATA_PATH = Path(ce("SCRAPER_DATA_PATH", "/tmp/data"))
    # Path to save the raw data to
    SCRAPER_RAW_DATA = Path(ce("SCRAPER_RAW_DATA", "/tmp/raw"))

    def __init__(self, url: str, **kwargs):
        """
        Initialize the scraper.

        Parameters
        ----------
        url : str
            URL to scrape
        **kwargs
            Optional keyword arguments for requests

        Examples
        --------
        >>> scraper = Scraper("https://example.com")
        >>> scraper = Scraper("https://api.example.com", timeout=30)
        """
        self.logger = create_logger()
        self.logger.debug("Setting url to %s", url)
        self.url = url
        if "method" not in kwargs:
            self.request_args = {
                "stream": True,
                "allow_redirects": True,
                "method": "GET",
                "verify": False,
            }
        else:
            self.request_args = {
                "stream": True,
                "allow_redirects": True,
                "verify": False,
            }
        self.request_args.update(**kwargs)
        # if not a dry run, create the output directories
        if not self.DRY_RUN:
            if not self.SCRAPER_DATA_PATH.exists():
                self.SCRAPER_DATA_PATH.mkdir(parents=True)
            if not self.SCRAPER_RAW_DATA.exists():
                self.SCRAPER_RAW_DATA.mkdir(parents=True)
        self.start_time = datetime.utcnow()
        self.scrape_end_time = None
        self.end_time = None

    @abstractmethod
    def request(self, url: str, **kwargs) -> Any:
        """
        Make a request to the specified URL.

        This method must be implemented by subclasses to define how
        the request is made (e.g., using requests, Selenium, etc.).

        Parameters
        ----------
        url : str
            The URL to request
        **kwargs
            Additional keyword arguments for the request

        Returns
        -------
        any
            The response data

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses

        Examples
        --------
        Implement in subclass:
            >>> def request(self, url, **kwargs):
            ...     response = requests.get(url, **kwargs)
            ...     return response.text
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, data: Any) -> Any:
        """
        Parse the retrieved data.

        This method must be implemented by subclasses to define how
        the retrieved data should be parsed and processed.

        Parameters
        ----------
        data : any
            The data to parse

        Returns
        -------
        any
            The parsed data

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses

        Examples
        --------
        Implement in subclass:
            >>> def parse(self, data):
            ...     soup = BeautifulSoup(data, 'html.parser')
            ...     return soup.find('title').text
        """
        raise NotImplementedError

    def scrape(self) -> Any:
        """
        Perform the complete scraping operation.

        This method combines the request and parse operations to
        perform a complete scraping operation.

        Returns
        -------
        any
            The final parsed result

        Examples
        --------
        >>> scraper = MyScraper("https://example.com")
        >>> result = scraper.scrape()
        >>> print(result)
        'Example Domain'
        """
        self.scrape_end_time = datetime.utcnow()
        self.logger.info(f"Scraping {self.url}")
        if isinstance(self.url, str):
            return self.scrape_single(self.url)
        elif isinstance(self.url, list):
            results = []
            for url in self.url:
                results.append(self.scrape_single(url))
            return results
        elif isinstance(self.url, collections.abc.Sequence):
            results = []
            for url in self.url:
                results.append(self.scrape_single(url))
            return results
        else:
            sys.exit(1)

    def scrape_single(self, url: str) -> Any:
        """Scrape a single website."""
        data = None  # set from self.request()

        for retry in range(self.SCRAPER_MAX_RETRIES):
            try:
                data = self.request(url, **self.request_args)
                break
            except requests.exceptions.SSLError as error:
                self.logger.critical(error)
                self.logger.critical(
                    f"Failed to connect to url: {url}, due to an \n"
                    " SSL issue. Check the request params "
                    " and fix the resulting issue."
                )
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                urllib.error.HTTPError,
                urllib.error.URLError,
                urllib3.exceptions.HTTPError,
                ConnectionError,
            ) as error:
                self.logger.warning(error)
                self.logger.warning("Connection timeout ... retry %d" % retry - 1)
                time.sleep(self.SCRAPER_TIMEOUT)
                continue
            except requests.exceptions.RequestException as error:
                self.logger.critical("An unknown request exception occurred" + " %s" % error)
                break
        else:
            # retries are exhausted
            msg = (
                f"{__class__.__name__} - Max numer of retries, "
                + f"{self.SCRAPER_MAX_RETRIES} exceeded for URL: "
                + f"{self.url}."
            )
            self.logger.critical(msg)
            data = None  # signal we did not get any data

        try:
            results = self.parse(data)
            return results
        except (
            selenium.common.exceptions.NoSuchAttributeException,
            selenium.common.exceptions.NoSuchFrameException,
            selenium.common.exceptions.NoSuchWindowException,
            selenium.common.exceptions.NoSuchAttributeException,
        ) as error:
            msg = "Selenium expected something to exist that did not: " + f"{error}"
            self.logger.critical(msg)
        except (
            selenium.common.exceptions.ElementClickInterceptedException,
            selenium.common.exceptions.ElementNotInteractableException,
            selenium.common.exceptions.ElementNotSelectableException,
            selenium.common.exceptions.StaleElementReferenceException,
            selenium.common.exceptions.UnexpectedTagNameException,
        ) as err:
            # selenium interaction object broken
            msg = "Selenium workflow logic interrupted by exception."
            self.logger.critical(msg + "\n:---:\n" + err)
        except Exception as error:
            msg = f"An {error} has occurred.\n"
            if hasattr(error, "__class__"):
                msg += f"Of {error.__class__} classinessy\n"
                if hasattr(error.__class__, "__name__"):
                    msg += "Named {error.__class__.__name__}"
            self.logger.critical(msg)
        # end of scrape_single

    def save_raw_pages(self, raw_page_text, override=False):
        """Save the raw page to a gzipped file."""
        if not self.SAVE_RAW_PAGES and not override:
            return
        timestamp = None
        if self.start_time is None:
            timestamp = str(datetime.strftime(datetime.utcnow(), "%Y-%m-%d-%H:%M:%S"))
        else:
            timestamp = str(self.start_time)

        datestamp = str(datetime.strftime(datetime.utcnow(), "%Y-%m-%d"))
        archive_dir = self.SCRAPER_RAW_DATA / datestamp
        if not archive_dir.exists():
            self.logger.info(f"Creating {str(archive_dir)}.")
            archive_dir.mkdir(parents=True, exist_ok=True)
        filename = RE_DOMAIN.search(self.url) + "-" + timestamp + "-rawpage.gz"
        filename = archive_dir / filename
        binary_str = str(raw_page_text).encode("utf-8")
        with gzip.open(str(filename), "wb") as f:
            f.write(binary_str)


class HTMLMixin:
    """
    Mixin class for HTML scraping.

    This mixin provides HTML-specific functionality for scrapers.
    It includes methods for working with HTML data and BeautifulSoup objects.

    Examples
    --------
    Use with Scraper base class:
        >>> class MyHTMLScraper(Scraper, HTMLMixin):
        ...     def request(self, url, **kwargs):
        ...         response = requests.get(url, **kwargs)
        ...         return response.text
        ...     
        ...     def parse(self, data):
        ...         soup = BeautifulSoup(data, 'html.parser')
        ...         return soup.find('h1').text
    """

    def request(self, url: str, **kwargs) -> str:
        """
        Make an HTTP request and return HTML content.

        Parameters
        ----------
        url : str
            The URL to request
        **kwargs
            Additional keyword arguments for requests

        Returns
        -------
        str
            The HTML content as a string

        Examples
        --------
        >>> scraper = MyHTMLScraper("https://example.com")
        >>> html = scraper.request("https://example.com")
        >>> print(html[:100])
        <!DOCTYPE html>...
        """
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None


class XMLMixin:
    """
    Mixin class for XML scraping.

    This mixin provides XML-specific functionality for scrapers.
    It includes methods for working with XML data and ElementTree objects.

    Examples
    --------
    Use with Scraper base class:
        >>> class MyXMLScraper(Scraper, XMLMixin):
        ...     def request(self, url, **kwargs):
        ...         response = requests.get(url, **kwargs)
        ...         return response.text
        ...     
        ...     def parse(self, data):
        ...         import xml.etree.ElementTree as ET
        ...         root = ET.fromstring(data)
        ...         return root.find('title').text
    """

    def request(self, url: str, **kwargs) -> str:
        """
        Make an HTTP request and return XML content.

        Parameters
        ----------
        url : str
            The URL to request
        **kwargs
            Additional keyword arguments for requests

        Returns
        -------
        str
            The XML content as a string

        Examples
        --------
        >>> scraper = MyXMLScraper("https://api.example.com/feed.xml")
        >>> xml = scraper.request("https://api.example.com/feed.xml")
        >>> print(xml[:100])
        <?xml version="1.0" encoding="UTF-8"?>...
        """
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None


class JSONMixin:
    """
    Mixin class for JSON scraping.

    This mixin provides JSON-specific functionality for scrapers.
    It includes methods for working with JSON data and dictionaries.

    Examples
    --------
    Use with Scraper base class:
        >>> class MyJSONScraper(Scraper, JSONMixin):
        ...     def request(self, url, **kwargs):
        ...         response = requests.get(url, **kwargs)
        ...         return response.json()
        ...     
        ...     def parse(self, data):
        ...         return data['results']
    """

    def request(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request and return JSON content.

        Parameters
        ----------
        url : str
            The URL to request
        **kwargs
            Additional keyword arguments for requests

        Returns
        -------
        dict
            The JSON content as a dictionary

        Examples
        --------
        >>> scraper = MyJSONScraper("https://api.example.com/data")
        >>> data = scraper.request("https://api.example.com/data")
        >>> print(data)
        {'key': 'value', 'results': [...]}
        """
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            return None
