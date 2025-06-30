#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a class responsible for initiating a webdriver."""
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
    Provide a wrapper for interacting with selenium's webdriver or requests.

    **Notes:**

    * chrome requires Google Chrome and chromedriver
    * firefox requires geckodriver

    :param url: The URL being requested.
    :param driver: The type of driver to use to connect.
    :param output: 'text' or 'json'.
    :param options: List of options to be passed to selenium.
    :param service_args: A list of service arguments to be passed to driver.
    :param timeout: How long to wait for an element to appear before timing out.
    :param implicit_wait: Set how long to wait on a DOM object.
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

        :param url: URL to connect to.
        :param driver: Underlying driver to use; can be 'chromedriver' or others.
        :param output: What kind of output we want; can be 'text' or others.
        :param options: Options for the underlying driver.
        :param service_args: Additional parameters for the driver.
        :param script: A script to run.
        :param timeout: Timeout for connecting.
        :param implicit_wait: Time to wait for desired components to render.
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
        Create a simple string representation of the WebDriver object.

        :return: A string describing the WebDriver object and its attributes.
        """
        msg = "WebDriver() Class with the following attributes:\n\tURL:"
        msg = msg + "%s\n\tDriver: %s\n" % (self.url, self.driver_type)
        if hasattr(self, "driver") and self.driver is not None:
            msg = msg + "\nDriver has been initialized"
        return msg

    def __enter__(self):
        """
        Return self upon entry via with statement.

        :return: The WebDriver instance.
        """
        return self

    def __exit__(self, wd_type, wd_value, wd_traceback):
        """
        Handle exiting the with statement.

        :param wd_type: The exception type.
        :param wd_value: The exception value.
        :param wd_traceback: The exception traceback.
        """
        self.close()

    def __del__(self):
        """
        Delete the webDriver object.

        This method ensures proper cleanup when the object is garbage collected.
        """
        self.close()

    def close(self):
        """
        Close the webdriver class.

        This method properly closes the driver and cleans up resources.
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

        :return: The response content (text or JSON) or the raw response object.
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
        Create driver based on Chrome.

        This method sets up a Chrome WebDriver with the specified options and service arguments.
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
        Get element by xpath.

        :param xpath: The xpath expression to locate the element.
        :return: The found element or None if not found.
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
        Get element by tag name.

        :param tag: The tag name to locate the element.
        :return: The found element or None if not found.
        """
        self.wait_for_element(tag, "tag")
        try:
            target = self.driver.find_element_by_tag_name(tag)
            return target
        except NoSuchElementException as e:
            self.logger.error(f"The tag {tag} does not exist: {e}")
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element seems stale: {e}")

    def get_id(self, id_name):
        """
        Get element by ID.

        :param id_name: The ID attribute to locate the element.
        :return: The found element or None if not found.
        """
        self.wait_for_element(id_name, "id")
        try:
            target = self.driver.find_element_by_id(id_name)
            return target
        except NoSuchElementException as e:
            self.logger.error(f"The tag {id_name} does not exist: {e}")
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element seems stale: {e}")

    def get_class(self, class_name):
        """
        Get element by class name.

        :param class_name: The class name to locate the element.
        :return: The found element or None if not found.
        """
        self.wait_for_element(class_name, "class")
        try:
            target = self.driver.find_element_by_class_name(class_name)
            return target
        except NoSuchElementException as e:
            self.logger.error(f"The class {class_name} does not exist: {e}")
        except WebDriverException as e:
            self.logger.error(f"Webdriver error occurred: {e}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element seems stale: {e}")

    def move_to_element(self, target):
        """
        Perform action chains move to element and click.

        :param target: The element to move to and click.
        """
        try:
            action_chains = ActionChains(self.driver).move_to_element(target)
            action_chains.click(target).perform()
        except NoSuchElementException as e:
            self.logger.error(f"The element {target} does not exist: {e}")
        except TimeoutException:
            self.logger.error(f"Connection timed out: {self.url}")
        except WebDriverException:
            self.logger.error("Webdriver error occurred: {e}")
        except StaleElementReferenceException as e:
            self.logger.error(f"Element seems stale: {e}")

    def request_phantomjs(self):
        """
        Create driver based on PhantomJS.

        This method sets up a PhantomJS WebDriver with the specified service arguments.
        """
        self.driver = webdriver.PhantomJS(service_args=self.service_args)

    def dump_out(self):
        """
        Dump the self.out attribute.

        :return: The value of the out attribute.
        """
        return self.out

    def driver_out(self):
        """
        Dump the self.driver attribute.

        :return: The value of the driver attribute.
        """
        return self.driver

    def wait_for_element(self, elem, elem_type, wait=None):
        """
        Wait for element to be available on the page.

        :param elem: The element identifier (xpath, id, class, etc.).
        :param elem_type: The type of element locator ('xpath', 'id', 'class', etc.).
        :param wait: The timeout in seconds (default: self.timeout).
        :raises ParserError: If the element type is not supported or element is not found.
        """
        if wait is None:
            wait = self.timeout
        try:
            if elem_type.lower() == "xpath":
                element_present = ec.presence_of_element_located((By.XPATH, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "id":
                element_present = ec.presence_of_element_located((By.ID, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "class":
                element_present = ec.presence_of_element_located((By.CLASS_NAME, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "css":
                element_present = ec.presence_of_element_located((By.CSS_SELECTOR, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "name":
                element_present = ec.presence_of_element_located((By.NAME, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "tag":
                element_present = ec.presence_of_element_located((By.TAG_NAME, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "link text":
                element_present = ec.presence_of_element_located((By.LINK_TEXT, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            elif elem_type.lower() == "partial link text":
                element_present = ec.presence_of_element_located((By.PARTIAL_LINK_TEXT, elem))
                WebDriverWait(self.driver, wait).until(element_present)
            else:
                raise ParserError(f"{elem_type} is not a supported type")
        except KeyError as e:
            self.logger.error(f"KeyError thrown {e}")
        # except WebDriverException as e:
        #     self.logger.error(f'WebDriver threw an exception {e}')
        except TimeoutException as e:
            self.logger.error(f"Timed out locating {elem}: {e}")
        except NoSuchElementException as e:
            msg = f"Element {elem} not found on page after "
            msg = msg + f"{wait} seconds: {e}"
            self.logger.error(msg)
            raise ParserError(msg)
        except Exception as e:
            self.logger.error(f"Unknown exception while waiting for element: " f"{e}")
