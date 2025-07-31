#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides a CAPTCHA Bypass Mixin."""

import cfscrape
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CfscrapeMixin:
    """Group together CFSCRAPE methods."""

    def request(self, url, verify=False, **kwargs):
        """Fetch data from `url` and return that in a Soup object.

        :param url: URL to fetch data from.
        :param verify: Whether to verify SSL certificates.
        :param kwargs: Additional arguments for cfscrape.
        :returns: BeautifulSoup object.
        """
        scrape = cfscrape.create_scraper(**kwargs)
        scrape.verify = verify
        html_text = scrape.get(url).text
        outage_data = Soup(html_text, "html.parser")
        return outage_data
