#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
`BaseScraper` sub-class to support selenium-based scraping

Unlike `BaseScraper`, users will sub-class from this class and **not**
use a mix-in class since `request()` is provided here.  However, users
will have to over-ride *two* functions:

* `interact()` that contains the Selenium web driver interactions to get
the outage data
* `parse()` which is overriden as with using the mix-in classes

`SeleniumScraper` is also an abstract-base class (ABC) to enforce not being
able to directly instantiate it, thus forcing users to subclass it.
"""

from bs4 import BeautifulSoup as Soup

from pygarden.scrapers.scraper import Scraper
from pygarden.scrapers.webdriver import WebDriver


class SeleniumScraper(Scraper):
    """
    Provides selenium-based scraping support

    This is a `BaseScraper` subclass and not a mix-in, as happens for the XML,
    JSON, and HTML scrapers.
    """

    def __init__(self, url, **kwargs):
        """
        Initialize the selenium scraper.

        :param url: URL to connect to.
        :param kwargs: Optional keyword arguments for requests/webdriver.
        """
        super().__init__(url, **kwargs)

    def request(self, url, soup_parser="html.parser", **kwargs):
        """
        Fetch data from `url` and return that in a Soup object.

        :param url: URL of the remote host.
        :param soup_parser: 'html.parser', 'xml', 'lxml', 'html5lib', or other
            valid BeautifulSoup parser.
        :param kwargs: Optional requests keyword arguments.
        :returns: BeautifulSoup object or None.
        """
        with WebDriver(url=url) as wd:
            # Do the fake mouse clicks to get the outage data, if any
            raw_data = self.interact(wd)

        if raw_data is not None:
            data = Soup(raw_data, soup_parser)
            return data

        return None

    def interact(self, web_driver):
        """
        Interact with the web driver to retrieve data.

        Override this method with the actual mouse clicks needed to retrieve your data.

        :param web_driver: Selenium webdriver from request() call.
        :returns: Raw data structure, or None if no data.
        """
        raise NotImplementedError
