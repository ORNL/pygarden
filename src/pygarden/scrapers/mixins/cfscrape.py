#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides a CAPTCHA Bypass Mixin."""

import urllib3
from bs4 import BeautifulSoup as Soup

try:
    import cfscrape
    _cfscrape_import_error = None
except ImportError as e:
    cfscrape = None
    _cfscrape_import_error = e

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CfscrapeMixin:
    """Group together CFSCRAPE methods."""

    def request(self, url, verify=False, **kwargs):
        """
        Fetch data from `url` and return that in a Soup object.

        :param url: URL to fetch data from.
        :param verify: Whether to verify SSL certificates.
        :param kwargs: Additional arguments for cfscrape.
        :returns: BeautifulSoup object.
        :raises ImportError: If cfscrape is not available or incompatible with urllib3.
        """
        if cfscrape is None:
            error_msg = "cfscrape is not available"
            if _cfscrape_import_error is not None:
                error_msg += f": {_cfscrape_import_error}"
            error_msg += (
                ". This may be due to urllib3 2.x incompatibility. "
                "Consider using cloudscraper or requests directly."
            )
            raise ImportError(error_msg)
        scrape = cfscrape.create_scraper(**kwargs)
        scrape.verify = verify
        html_text = scrape.get(url).text
        outage_data = Soup(html_text, "html.parser")
        return outage_data
