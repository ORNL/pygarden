#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides a CAPTCHA Bypass Mixin."""
import re

import cloudscraper
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CloudscraperMixin:
    """
    Cloud scraper will attempt to bypass captcha settings.

    This mixin provides CAPTCHA bypass capabilities using cloudscraper
    for web scraping operations that may encounter CAPTCHA challenges.
    """

    def request(self, url, n_retries=3, **kwargs):
        """
        Fetch data from `url` and return that in a Soup object.

        :param url: The URL to request.
        :param n_retries: The number of retry attempts (default: 3).
        :param kwargs: Additional keyword arguments for the request.
        :return: A BeautifulSoup object if successful, None if CAPTCHA persists.
        """
        for i in range(n_retries):
            scraper = cloudscraper.create_scraper()
            html_text = scraper.get(url).text
            if not re.search(".*captcha.*", html_text):
                outage_data = Soup(html_text, "html.parser")
                return outage_data
        return None
