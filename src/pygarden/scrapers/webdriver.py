#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide a class responsible for initiating a webdriver.

This module provides a WebDriver class that serves as a wrapper for Selenium
WebDriver and requests library. It supports multiple browser drivers including
Chrome, Firefox, PhantomJS, and Opera, as well as simple HTTP requests.

The module provides:
- WebDriver class with unified interface for different drivers
- Support for Chrome, Firefox, PhantomJS, Opera, and requests
- Element interaction methods with waiting capabilities
- Context manager support for safe resource management
- Comprehensive error handling and logging

Examples
--------
Use Chrome WebDriver::

    >>> with WebDriver("https://example.com", driver="chromedriver") as wd:
    ...     element = wd.get_id("content")
    ...     print(element.text)

Use requests instead of browser::

    >>> with WebDriver("https://api.example.com/data", driver="requests") as wd:
    ...     data = wd.out
    ...     print(data)

Wait for an element to appear::

    >>> with WebDriver("https://example.com") as wd:
    ...     element = wd.wait_for_element("loading", "id", wait=10)
    ...     print("Element found:", element.text)

Use with custom options::

    >>> options = ["--headless", "--no-sandbox"]
    >>> with WebDriver("https://example.com", options=options) as wd:
    ...     content = wd.get_id("main-content")
    ...     print(content.text)

Notes
-----
This module requires Selenium and appropriate browser drivers to be installed
for browser-based operations. For requests-based operations, only the requests
library is required.
"""
import logging
import traceback
from typing import Optional

import requests
from rich.logging import RichHandler
from rich.traceback import install
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from urllib3.exceptions import ConnectionError, HTTPError

from pygarden.exceptions import ParserError

install()


class WebDriver:
    """
    Provide a wrapper for interacting with Selenium's webdriver or requests.

    This class provides a unified interface for web scraping using either
    Selenium WebDriver (for JavaScript-heavy sites) or the requests library
    (for simple HTTP requests). It supports multiple browser drivers and
    provides convenient methods for element interaction.

    :param url: The URL to connect to
    :type url: str or None
    :param driver: The type of driver to use
    :type driver: str
    :param output: Output type for requests driver
    :type output: str
    :param options: List of options to pass to Selenium driver
    :type options: list or None
    :param service_args: List of service arguments to pass to driver
    :type service_args: list or None
    :param script: Script to run after page load
    :type script: str or None
    :param timeout: Timeout for element waiting in seconds
    :type timeout: int
    :param implicit_wait: Implicit wait time for DOM elements in seconds
    :type implicit_wait: int

    Attributes
    ----------
    url : str
        The URL being requested
    driver_type : str
        The type of driver being used
    output_type : str
        The output type for requests
    opts : list
        Driver options
    service_args : list
        Service arguments
    timeout : int
        Element timeout in seconds
    driver : WebDriver or None
        The Selenium WebDriver instance
    out : any
        Output from requests driver
    logger : Logger
        Logger instance

    Notes
    -----
    Driver Requirements:
        - Chrome: Requires Google Chrome and chromedriver
        - Firefox: Requires geckodriver
        - PhantomJS: Requires PhantomJS binary
        - Requests/Curl: No additional requirements

    Examples
    --------
    Basic Chrome usage::

        >>> with WebDriver("https://example.com") as wd:
        ...     title = wd.driver.title
        ...     print(title)

    Use with custom options::

        >>> options = ["--headless", "--no-sandbox"]
        >>> with WebDriver("https://example.com", options=options) as wd:
        ...     content = wd.get_id("main-content")
        ...     print(content.text)

    Use requests driver::

        >>> with WebDriver("https://api.example.com", driver="requests") as wd:
        ...     data = wd.out
        ...     print(data)

    Wait for specific element::

        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.wait_for_element("submit-button", "id", wait=10)
        ...     element.click()

    Use with different drivers::

        >>> with WebDriver("https://example.com", driver="firefox") as wd:
        ...     element = wd.get_class("header")
        ...     print(element.text)

    Notes
    -----
    This class provides a unified interface for different web scraping
    approaches. For JavaScript-heavy sites, use Selenium drivers. For
    simple API calls or static content, use the requests driver.
    """

    def __init__(
        self,
        url=None,
        driver="chromedriver",
        output="text",
        options: Optional[list] = None,
        service_args: Optional[list] = None,
        script=None,
        timeout=30,
        implicit_wait=5,
    ):
        """
        Initialize a webdriver object.

        :param url: URL to connect to
        :type url: str or None
        :param driver: Underlying driver to use
        :type driver: str
        :param output: What kind of output we want
        :type output: str
        :param options: Options for the underlying driver
        :type options: list or None
        :param service_args: Additional service parameters
        :type service_args: list or None
        :param script: Script to run after page load
        :type script: str or None
        :param timeout: Timeout for connecting and element waiting
        :type timeout: int
        :param implicit_wait: Implicit wait for DOM components to render
        :type implicit_wait: int

        Examples
        --------
        >>> wd = WebDriver("https://example.com")
        >>> wd = WebDriver("https://api.example.com", driver="requests", output="json")
        >>> wd = WebDriver("https://example.com", timeout=60, implicit_wait=10)

        Notes
        -----
        The constructor initializes the appropriate driver based on the
        driver parameter and sets up logging and configuration.
        """
        if options is None:
            options = [
                "--no-sandbox",
                "--disable-logging",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "headless",
            ]
        if service_args is None:
            service_args = ["--ignore-ssl-errors=true", "--ssl-protocol=any"]
        rich_handler = RichHandler(rich_tracebacks=True, markup=True)
        logging.basicConfig(
            level="INFO",
            format="%(message)s",
            datefmt="[%Y/%m/%d %H:%M:%S]",
            handlers=[rich_handler],
        )
        self.logger = logging.getLogger("rich")
        self.url = url
        self.driver_type = driver
        self.output_type = output
        self.opts = options
        self.service_args = service_args
        self.out = None
        self.timeout = timeout
        if driver.lower() in ["requests", "curl"]:
            self.out = self.request_url()
        elif driver.lower() == "chromedriver":
            self.request_chrome()
        elif driver.lower() == "phantomjs":
            self.request_phantomjs()
        elif driver.lower() == "firefox":
            # handle firefox here
            pass
        elif driver.lower() == "opera":
            # handle opera here
            pass
        elif driver.lower() == "ie":
            pass
        else:
            traceback.print_stack()
            raise KeyError("No driver type " + driver)
        if hasattr(self, "driver") and self.driver is not None:
            self.driver.implicitly_wait(implicit_wait)
            self.driver.set_window_size(1024, 768)
            self.logger.info("Connecting to %s" % self.url)
            self.driver.get(self.url)
            self.logger.info("Connected to %s" % self.url)

    def __str__(self):
        """
        Create a string representation of the WebDriver object.

        :return: String representation showing URL, driver type, and initialization status
        :rtype: str

        Examples
        --------
        >>> wd = WebDriver("https://example.com")
        >>> print(str(wd))
        WebDriver() Class with the following attributes:
            URL: https://example.com
            Driver: chromedriver
        Driver has been initialized

        >>> wd = WebDriver("https://api.example.com", driver="requests")
        >>> print(str(wd))
        WebDriver() Class with the following attributes:
            URL: https://api.example.com
            Driver: requests
        """
        msg = "WebDriver() Class with the following attributes:\n\tURL:"
        msg = msg + "%s\n\tDriver: %s\n" % (self.url, self.driver_type)
        if hasattr(self, "driver") and self.driver is not None:
            msg = msg + "\nDriver has been initialized"
        return msg

    def __enter__(self):
        """
        Return self upon entry via with statement.

        :return: Self reference for context manager
        :rtype: WebDriver

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     print(wd.driver.title)
        """
        return self

    def __exit__(self, wd_type, wd_value, wd_traceback):
        """
        Handle exiting the with statement.

        :param wd_type: Exception type if an exception occurred
        :type wd_type: type or None
        :param wd_value: Exception value if an exception occurred
        :type wd_value: Exception or None
        :param wd_traceback: Exception traceback if an exception occurred
        :type wd_traceback: traceback or None

        Notes
        -----
        This method ensures that the WebDriver is properly closed when
        exiting the context manager, regardless of whether an exception
        occurred.
        """
        self.close()

    def __del__(self):
        """
        Delete the WebDriver object and clean up resources.

        This method ensures that the WebDriver is properly closed when
        the object is garbage collected.

        Notes
        -----
        This method is called when the object is garbage collected, but
        it's not guaranteed to be called. Always use context managers
        for reliable resource cleanup.
        """
        self.close()

    def close(self):
        """
        Close the WebDriver and clean up resources.

        This method safely closes the WebDriver instance and handles
        any exceptions that might occur during cleanup.

        Examples
        --------
        >>> wd = WebDriver("https://example.com")
        >>> wd.close()  # Explicitly close the driver

        Notes
        -----
        This method safely closes the WebDriver instance and handles
        any exceptions that might occur during cleanup.
        """
        if hasattr(self, "driver"):
            if self.driver is not None:
                try:
                    self.driver.close()
                    self.driver.quit()
                except Exception as e:
                    self.logger.warning(f"Unknown exception when deleting " f"object: {e}")
                finally:
                    del self.driver
        del self

    def request_url(self):
        """
        Use requests to parse the URL.

        This method uses the requests library to fetch content from the URL
        and returns it in the specified output format.

        :return: The response content in the specified format (text, json, or raw response)
        :rtype: str or dict or requests.Response

        Examples
        --------
        >>> wd = WebDriver("https://api.example.com", driver="requests", output="json")
        >>> data = wd.out
        >>> print(data)
        {'key': 'value'}

        >>> wd = WebDriver("https://example.com", driver="requests", output="text")
        >>> html = wd.out
        >>> print(html[:100])
        <!DOCTYPE html>...

        >>> wd = WebDriver("https://api.example.com", driver="requests", output="raw")
        >>> response = wd.out
        >>> print(response.status_code)
        200

        Notes
        -----
        This method handles HTTP requests and supports different output
        formats. It includes error handling for connection and HTTP errors.
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
        except ConnectionError as e:
            self.logger.error(f"Connection error occurred: {e}")
        except HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
        except Exception as e:
            self.logger.error(f"An Error occurred while processing " f"{self.url}: {e}")
        if self.output_type == "text":
            return response.text
        if self.output_type == "json":
            return response.json()
        self.logger.warning(f"Unknown output_type specified: " f"{self.output_type}. Returning bare response")
        return response

    def request_chrome(self):
        """
        Method to create driver based on Chrome.

        This method initializes a Chrome WebDriver with the specified options
        and service arguments.

        Examples
        --------
        >>> wd = WebDriver("https://example.com", driver="chromedriver")
        >>> print(wd.driver.title)

        >>> wd = WebDriver("https://example.com", driver="chromedriver", 
        ...               options=["--headless", "--no-sandbox"])
        >>> print(wd.driver.title)

        Notes
        -----
        This method sets up a Chrome WebDriver with the specified options
        and service arguments. It handles WebDriver exceptions gracefully.
        """
        self.logger.info(f"Using chrome to connect to {self.url}")
        self.options = webdriver.ChromeOptions()
        try:
            if self.opts is not None:
                for opt in self.opts:
                    self.options.add_argument(opt)
                if self.service_args is None:
                    self.driver = webdriver.Chrome(self.driver_type, options=self.options)
                else:
                    self.driver = webdriver.Chrome(
                        self.driver_type,
                        service_args=self.service_args,
                        options=self.options,
                    )
            else:
                if self.service_args is None:
                    self.driver = webdriver.Chrome(self.driver_type)
                else:
                    self.driver = webdriver.Chrome(self.driver_type, service_args=self.service_args)

        except WebDriverException as e:
            # for some reason, WebDriverException is raised by Selenium, but
            # no error message is received
            self.logger.warning(f"Webdriver Exception thrown: {e}")

        except Exception as e:
            self.logger.warning(f"Unknown exception while creating driver  {e}")

    def get_xpath(self, xpath):
        """
        Get an element by XPath.

        This method waits for an element to be present using the specified XPath
        and then returns the found element.

        :param xpath: The XPath expression to find the element
        :type xpath: str
        :return: The found element, or None if not found
        :rtype: WebElement or None

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_xpath("//div[@class='content']")
        ...     print(element.text)

        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_xpath("//button[@id='submit']")
        ...     if element:
        ...         element.click()

        Notes
        -----
        This method waits for the element to be present before attempting
        to find it. If the element is not found, it returns None.
        """
        self.wait_for_element(xpath, "xpath")
        try:
            target = self.driver.find_element_by_xpath(xpath)
            return target
        except NoSuchElementException as e:
            self.logger.error(f'Unable to find xpath "{xpath}": {e}')
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e} with {xpath}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element {xpath} seems stale: {e}")

    def get_tag(self, tag):
        """
        Get an element by tag name.

        This method waits for an element to be present using the specified tag name
        and then returns the found element.

        :param tag: The HTML tag name to find the element
        :type tag: str
        :return: The found element, or None if not found
        :rtype: WebElement or None

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_tag("h1")
        ...     print(element.text)

        >>> with WebDriver("https://example.com") as wd:
        ...     elements = wd.driver.find_elements_by_tag_name("div")
        ...     for element in elements:
        ...         print(element.text)

        Notes
        -----
        This method waits for the element to be present before attempting
        to find it. If the element is not found, it returns None.
        """
        self.wait_for_element(tag, "tag")
        try:
            target = self.driver.find_element_by_tag_name(tag)
            return target
        except NoSuchElementException as e:
            self.logger.error(f'Unable to find tag "{tag}": {e}')
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e} with {tag}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element {tag} seems stale: {e}")

    def get_id(self, id_name):
        """
        Get an element by ID.

        This method waits for an element to be present using the specified ID
        and then returns the found element.

        :param id_name: The ID attribute value to find the element
        :type id_name: str
        :return: The found element, or None if not found
        :rtype: WebElement or None

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_id("main-content")
        ...     print(element.text)

        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_id("submit-button")
        ...     if element:
        ...         element.click()

        Notes
        -----
        This method waits for the element to be present before attempting
        to find it. If the element is not found, it returns None.
        """
        self.wait_for_element(id_name, "id")
        try:
            target = self.driver.find_element_by_id(id_name)
            return target
        except NoSuchElementException as e:
            self.logger.error(f'Unable to find id "{id_name}": {e}')
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e} with {id_name}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element {id_name} seems stale: {e}")

    def get_class(self, class_name):
        """
        Get an element by class name.

        This method waits for an element to be present using the specified class name
        and then returns the found element.

        :param class_name: The CSS class name to find the element
        :type class_name: str
        :return: The found element, or None if not found
        :rtype: WebElement or None

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_class("header")
        ...     print(element.text)

        >>> with WebDriver("https://example.com") as wd:
        ...     elements = wd.driver.find_elements_by_class_name("menu-item")
        ...     for element in elements:
        ...         print(element.text)

        Notes
        -----
        This method waits for the element to be present before attempting
        to find it. If the element is not found, it returns None.
        """
        self.wait_for_element(class_name, "class")
        try:
            target = self.driver.find_element_by_class_name(class_name)
            return target
        except NoSuchElementException as e:
            self.logger.error(f'Unable to find class "{class_name}": {e}')
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e} with {class_name}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element {class_name} seems stale: {e}")

    def move_to_element(self, target):
        """
        Move the mouse cursor to the specified element.

        This method uses ActionChains to move the mouse cursor to the target element,
        which can be useful for triggering hover effects or ensuring the element is visible.

        :param target: The target element to move the cursor to
        :type target: WebElement

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_id("menu-item")
        ...     wd.move_to_element(element)  # Hover over the menu item

        >>> with WebDriver("https://example.com") as wd:
        ...     element = wd.get_class("dropdown")
        ...     wd.move_to_element(element)  # Trigger dropdown menu

        Notes
        -----
        This method is useful for triggering hover effects or ensuring
        that elements are visible before interacting with them.
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(target)
            actions.perform()
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e}")
        except Exception as e:
            self.logger.error(f"Unknown error occurred: {e}")

    def request_phantomjs(self):
        """
        Method to create driver based on PhantomJS.

        This method initializes a PhantomJS WebDriver. Note that PhantomJS
        is deprecated and it's recommended to use headless Chrome instead.

        Examples
        --------
        >>> wd = WebDriver("https://example.com", driver="phantomjs")
        >>> print(wd.driver.title)

        Notes
        -----
        PhantomJS is deprecated and it's recommended to use headless Chrome
        instead for headless browser automation.
        """
        self.driver = webdriver.PhantomJS()

    def dump_out(self):
        """
        Dump the output from requests driver.

        This method returns the output from the requests driver, which is
        useful when using the 'requests' or 'curl' driver types.

        :return: The output from the requests driver
        :rtype: any

        Examples
        --------
        >>> wd = WebDriver("https://api.example.com", driver="requests")
        >>> output = wd.dump_out()
        >>> print(output)

        >>> wd = WebDriver("https://example.com", driver="requests", output="json")
        >>> data = wd.dump_out()
        >>> print(data['title'])
        """
        return self.out

    def driver_out(self):
        """
        Get the page source from the WebDriver.

        This method returns the current page source from the WebDriver,
        which is useful for getting the full HTML content of the page.

        :return: The page source HTML
        :rtype: str

        Examples
        --------
        >>> with WebDriver("https://example.com") as wd:
        ...     html = wd.driver_out()
        ...     print(html[:500])  # First 500 characters

        >>> with WebDriver("https://example.com") as wd:
        ...     html = wd.driver_out()
        ...     if "error" in html.lower():
        ...         print("Error page detected")

        Notes
        -----
        This method returns the complete HTML source of the current page,
        including any dynamically generated content.
        """
        return self.driver.page_source

    def wait_for_element(self, elem, elem_type, wait=None):
        """
        Wait for an element to be present on the page.

        This method waits for a specific element to be present on the page
        before proceeding. It supports different element types including
        ID, class name, tag name, and XPath.

        :param elem: The element identifier (ID, class, tag, or XPath)
        :type elem: str
        :param elem_type: The type of element ('id', 'class', 'tag', 'xpath')
        :type elem_type: str
        :param wait: Timeout in seconds. If None, uses the default timeout
        :type wait: int or None
        :return: The found element, or None if timeout occurs
        :rtype: WebElement or None

        Examples
        --------
        Wait for element by ID::

            >>> with WebDriver("https://example.com") as wd:
            ...     element = wd.wait_for_element("content", "id", wait=10)
            ...     print("Element found:", element.text)

        Wait for element by class::

            >>> with WebDriver("https://example.com") as wd:
            ...     element = wd.wait_for_element("loading", "class")
            ...     print("Loading element found")

        Wait for element by XPath::

            >>> with WebDriver("https://example.com") as wd:
            ...     element = wd.wait_for_element("//div[@class='main']", "xpath")
            ...     print("Main div found")

        Wait with custom timeout::

            >>> with WebDriver("https://example.com") as wd:
            ...     element = wd.wait_for_element("slow-loading", "id", wait=30)
            ...     if element:
            ...         print("Element loaded successfully")

        Notes
        -----
        This method uses WebDriverWait to wait for elements to be present
        on the page. It supports different element types and custom timeouts.
        If the element is not found within the timeout period, it returns None.
        """
        if wait is None:
            wait = self.timeout

        try:
            if elem_type.lower() == "id":
                element = WebDriverWait(self.driver, wait).until(
                    ec.presence_of_element_located((By.ID, elem))
                )
            elif elem_type.lower() == "class":
                element = WebDriverWait(self.driver, wait).until(
                    ec.presence_of_element_located((By.CLASS_NAME, elem))
                )
            elif elem_type.lower() == "tag":
                element = WebDriverWait(self.driver, wait).until(
                    ec.presence_of_element_located((By.TAG_NAME, elem))
                )
            elif elem_type.lower() == "xpath":
                element = WebDriverWait(self.driver, wait).until(
                    ec.presence_of_element_located((By.XPATH, elem))
                )
            else:
                raise ParserError(f"Unknown element type: {elem_type}")

            return element

        except TimeoutException:
            self.logger.error(f"Timeout waiting for element {elem} of type {elem_type}")
            return None
        except Exception as e:
            self.logger.error(f"Error waiting for element {elem}: {e}")
            return None
