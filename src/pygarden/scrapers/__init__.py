"""
Initialize the scrapers module.

This module provides web scraping functionality including base scraper classes,
Selenium support, and various data format mixins (HTML, XML, JSON, CSV).

The module provides:
- Base Scraper class with common scraping functionality
- SeleniumScraper for JavaScript-heavy websites
- Data format mixins (HTML, XML, JSON, CSV)
- WebDriver wrapper for browser automation
- Static utilities for scraping operations

Examples
--------
Import base scraper::

    >>> from pygarden.scrapers import Scraper, HTMLMixin

Import Selenium scraper::

    >>> from pygarden.scrapers import SeleniumScraper

Import CSV scraper::

    >>> from pygarden.scrapers import CSVScraper

Create a custom HTML scraper::

    >>> class MyScraper(HTMLMixin, Scraper):
    ...     def parse(self, data):
    ...         return data.find('title').text

Create a Selenium scraper::

    >>> class MySeleniumScraper(SeleniumScraper):
    ...     def interact(self, web_driver):
    ...         return web_driver.page_source
    ...     def parse(self, data):
    ...         return data.find('h1').text

Notes
-----
This module provides a comprehensive web scraping framework with support
for both static and dynamic content. The mixin pattern allows for flexible
composition of different data format handlers.
"""

from pygarden.scrapers.scraper import Scraper, HTMLMixin, JSONMixin, XMLMixin
from pygarden.scrapers.seleniumscraper import SeleniumScraper
from pygarden.scrapers.csvs import CSVScraper

__all__ = [
    "Scraper",
    "HTMLMixin",
    "JSONMixin",
    "XMLMixin",
    "SeleniumScraper",
    "CSVScraper",
]
