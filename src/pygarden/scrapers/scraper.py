# noqa: C901
"""Provide a scraper base class, which other scraper types are built."""

import collections.abc
import gzip
import re
import sys
import time
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import requests
import selenium.common.exceptions
import urllib3.exceptions

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

RE_DOMAIN = re.compile("https?://([A-Za-z_0-9.-]+).*")


__authors__ = ["grantjn@ornl.gov", "colletim@ornl.gov"]


class Scraper(ABC):
    """
    Abstract base class for all your scraping and parsing needs.

    Environmental variables that alter behavior:
        * `DRY_RUN`: if True, do not write to any files
        * `SAVE_RAW_PAGES`: if True, save the raw data from the website for
                            later inspection
        * `SCRAPER_MAX_RETRIES`: how many times to try before giving up
        * `SCRAPER_TIMEOUT`: how long in seconds do we wait for a site to
                             respond?
        * `SCRAPER_DATA_PATH`: path to save retrieved data to
        * `SCRAPER_RAW_PATH`: path to save raw webpage to
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

    def __init__(self, url, **kwargs):
        """
        Initialize the scraper object and assign internal states.

        The `**kwargs` is a generic way to tailor `request()`.

        If `url` is a sequence, the individual URLs will be iteratively
        processed independent of one another.

        :param url: One or more URLs to be parsed by this scraper. Accepts
                    types of `str` or `list`.
        :param kwargs: Optional keyword arguments that are passed to
                       `request`.
        """
        self.log = create_logger()
        self.log.debug("Setting url to %s", url)
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
    def parse(self, data):
        """
        Parse method for the inherited classes to use for logic.

        :param data: Data structured to be parsed; likely in the form of
                     JSON, XML, BeautifulSoup, etc, depending on the MIXIN.
        """
        raise NotImplementedError

    def scrape(self):
        """Scrape a website."""

        def do_scrape(url):
            """
            Scrape a website and parse the data.

            :param url: URL to scrape.
            :type url: str
            :returns: Parsed data.
            :rtype: dict
            """
            data = None  # set from self.request()

            for retry in range(self.SCRAPER_MAX_RETRIES):
                try:
                    data = self.request(url, **self.request_args)
                    break
                except requests.exceptions.SSLError as error:
                    self.log.critical(error)
                    self.log.critical(
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
                    self.log.warning(error)
                    self.log.warning("Connection timeout ... retry %d" % retry - 1)
                    time.sleep(self.SCRAPER_TIMEOUT)
                    continue
                except requests.exceptions.RequestException as error:
                    self.log.critical("An unknown request exception occurred" + " %s" % error)
                    break
            else:
                # retries are exhausted
                msg = (
                    f"{__class__.__name__} - Max numer of retries, "
                    + f"{self.SCRAPER_MAX_RETRIES} exceeded for URL: "
                    + f"{self.url}."
                )
                self.log.critical(msg)
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
                self.log.critical(msg)
            except (
                selenium.common.exceptions.ElementClickInterceptedException,
                selenium.common.exceptions.ElementNotInteractableException,
                selenium.common.exceptions.ElementNotSelectableException,
                selenium.common.exceptions.StaleElementReferenceException,
                selenium.common.exceptions.UnexpectedTagNameException,
            ) as err:
                # selenium interaction object broken
                msg = "Selenium workflow logic interrupted by exception."
                self.log.critical(msg + "\n:---:\n" + err)
            except Exception as error:
                msg = f"An {error} has occurred.\n"
                if hasattr(error, "__class__"):
                    msg += f"Of {error.__class__} classinessy\n"
                    if hasattr(error.__class__, "__name__"):
                        msg += "Named {error.__class__.__name__}"
                self.log.critical(msg)
            # end of do_scrape

        self.scrape_end_time = datetime.utcnow()
        self.log.info(f"Scraping {self.url}")
        if isinstance(self.url, str):
            do_scrape(self.url)
        elif isinstance(self.url, list):
            for url in self.url:
                do_scrape(url)
        elif isinstance(self.url, collections.abc.Sequence):
            for url in self.url:
                do_scrape(url)
        else:
            sys.exit(1)

    def save_raw_pages(self, raw_page_text, override=False):
        """Save the raw page to a gzipped file.

        :param raw_page_text: Raw page content to save.
        :param override: Whether to override existing files.
        """
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
            self.log.info(f"Creating {str(archive_dir)}.")
            archive_dir.mkdir(parents=True, exist_ok=True)
        filename = RE_DOMAIN.search(self.url) + "-" + timestamp + "-rawpage.gz"
        filename = archive_dir / filename
        binary_str = str(raw_page_text).encode("utf-8")
        with gzip.open(str(filename), "wb") as f:
            f.write(binary_str)
