#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaseScraper sub-class to support selenium-based scraping.

This module provides a SeleniumScraper class that extends the base Scraper
class to support web scraping using Selenium WebDriver. Unlike the base
scraper, users will sub-class from this class and **not** use a mix-in
class since `request()` is provided here. However, users will have to
override *two* functions:

* `interact()` that contains the Selenium web driver interactions to get
  the outage data
* `parse()` which is overridden as with using the mix-in classes

SeleniumScraper is also an abstract-base class (ABC) to enforce not being
able to directly instantiate it, thus forcing users to subclass it.

The module provides:
- SeleniumScraper abstract base class
- WebDriver integration for dynamic content
- Custom interaction and parsing methods
- BeautifulSoup integration for HTML parsing

Examples
--------
Create a custom Selenium scraper::

    >>> class MySeleniumScraper(SeleniumScraper):
    ...     def interact(self, web_driver):
    ...         # Custom Selenium interactions
    ...         element = web_driver.find_element_by_id("data")
    ...         return element.get_attribute("innerHTML")
    ...     
    ...     def parse(self, data):
    ...         # Parse the retrieved data
    ...         soup = BeautifulSoup(data, 'html.parser')
    ...         return soup.find('div').text

Create a weather scraper::

    >>> class WeatherScraper(SeleniumScraper):
    ...     def interact(self, web_driver):
    ...         # Click on weather tab
    ...         tab = web_driver.find_element_by_id("weather-tab")
    ...         tab.click()
    ...         return web_driver.page_source
    ...     
    ...     def parse(self, data):
    ...         soup = BeautifulSoup(data, 'html.parser')
    ...         temp = soup.find('span', class_='temperature').text
    ...         return {'temperature': temp}

Notes
-----
This class requires Selenium WebDriver and BeautifulSoup to be installed.
The interact() method must be implemented by subclasses to define the
specific Selenium interactions needed for each website.
"""
from bs4 import BeautifulSoup as Soup

from pygarden.scrapers.scraper import Scraper
from pygarden.scrapers.webdriver import WebDriver


class SeleniumScraper(Scraper):
    """
    Provides selenium-based scraping support.

    This is a `BaseScraper` subclass and not a mix-in, as happens for the XML,
    JSON, and HTML scrapers. It provides a complete interface for Selenium-based
    web scraping with custom interaction and parsing capabilities.

    :param url: The URL to scrape
    :type url: str
    :param **kwargs: Optional keyword arguments for requests/webdriver

    Attributes
    ----------
    url : str
        The URL being scraped
    request_args : dict
        Arguments for the request method

    Examples
    --------
    Create a custom scraper::

        >>> class WeatherScraper(SeleniumScraper):
        ...     def interact(self, web_driver):
        ...         # Click on weather tab
        ...         tab = web_driver.find_element_by_id("weather-tab")
        ...         tab.click()
        ...         return web_driver.page_source
        ...     
        ...     def parse(self, data):
        ...         soup = BeautifulSoup(data, 'html.parser')
        ...         temp = soup.find('span', class_='temperature').text
        ...         return {'temperature': temp}

    Create a login scraper::

        >>> class LoginScraper(SeleniumScraper):
        ...     def interact(self, web_driver):
        ...         # Fill login form
        ...         username = web_driver.find_element_by_id("username")
        ...         password = web_driver.find_element_by_id("password")
        ...         username.send_keys("user@example.com")
        ...         password.send_keys("password123")
        ...         
        ...         # Submit form
        ...         submit = web_driver.find_element_by_id("submit")
        ...         submit.click()
        ...         
        ...         return web_driver.page_source
        ...     
        ...     def parse(self, data):
        ...         soup = BeautifulSoup(data, 'html.parser')
        ...         return soup.find('div', class_='dashboard').text

    Notes
    -----
    This class provides a complete Selenium-based scraping interface.
    Subclasses must implement both interact() and parse() methods.
    The interact() method handles Selenium WebDriver interactions,
    while parse() method handles data extraction from the retrieved content.
    """

    def __init__(self, url, **kwargs):
        """
        Initialize the selenium scraper.

        :param url: URL to connect to
        :type url: str
        :param **kwargs: Optional keyword arguments for requests/webdriver

        Examples
        --------
        >>> scraper = MySeleniumScraper("https://example.com")
        >>> scraper = MySeleniumScraper("https://example.com", timeout=30)
        """
        super().__init__(url, **kwargs)

    def request(self, url, soup_parser="html.parser", **kwargs):
        """
        Fetch data from `url` and return that in a Soup object.

        This method uses Selenium WebDriver to fetch data from the specified URL.
        It calls the `interact()` method to perform custom Selenium interactions
        and then parses the result using BeautifulSoup.

        :param url: URL of the remote host
        :type url: str
        :param soup_parser: BeautifulSoup parser to use
        :type soup_parser: str
        :param **kwargs: Optional requests keyword arguments
        :return: Parsed HTML data as BeautifulSoup object, or None if no data retrieved
        :rtype: BeautifulSoup or None

        Examples
        --------
        >>> scraper = MySeleniumScraper("https://example.com")
        >>> soup = scraper.request("https://example.com")
        >>> print(soup.title.string)
        'Example Domain'

        Use with custom parser::

            >>> soup = scraper.request("https://example.com", soup_parser="lxml")
            >>> soup = scraper.request("https://example.com", soup_parser="html5lib")

        Notes
        -----
        This method creates a WebDriver instance, calls the interact() method
        to perform custom interactions, and then parses the result using
        BeautifulSoup. The soup_parser parameter determines which parser
        BeautifulSoup uses ('html.parser', 'xml', 'lxml', 'html5lib').
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

        This method must be overridden by subclasses to implement the specific
        Selenium interactions needed to retrieve data from the target website.

        :param web_driver: Selenium webdriver from request() call
        :type web_driver: WebDriver
        :return: Raw data structure, or None if no data found
        :rtype: str or None
        :raises NotImplementedError: This method must be implemented by subclasses

        Examples
        --------
        Override this method in your subclass::

            >>> def interact(self, web_driver):
            ...     # Find and click a button
            ...     button = web_driver.find_element_by_id("load-data")
            ...     button.click()
            ...     
            ...     # Wait for data to load
            ...     import time
            ...     time.sleep(2)
            ...     
            ...     # Return the page source
            ...     return web_driver.page_source

        Wait for specific element::

            >>> def interact(self, web_driver):
            ...     # Wait for content to load
            ...     element = web_driver.wait_for_element("content", "id", wait=10)
            ...     if element:
            ...         return web_driver.page_source
            ...     return None

        Handle dynamic content::

            >>> def interact(self, web_driver):
            ...     # Scroll to load more content
            ...     web_driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            ...     import time
            ...     time.sleep(3)
            ...     return web_driver.page_source

        Notes
        -----
        This method should contain all the Selenium WebDriver interactions
        needed to retrieve the desired data. Common operations include:
        - Finding and clicking elements
        - Filling forms
        - Waiting for content to load
        - Scrolling pages
        - Handling popups or modals
        
        The method should return the raw HTML content (usually page_source)
        that will be parsed by the parse() method.
        """
        raise NotImplementedError
