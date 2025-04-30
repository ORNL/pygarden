#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides a CAPTCHA Bypass Mixin."""
import re

import cloudscraper
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CloudscraperMixin:
    """Cloud scraper will attempt to bypass captcha settings."""

    def request(self, url, n_retries=3, **kwargs):
        """Fetch data from `url` and return that in a Soup object."""
        for i in range(n_retries):
            scraper = cloudscraper.create_scraper()
            html_text = scraper.get(url).text
            if not re.search(".*captcha.*", html_text):
                outage_data = Soup(html_text, "html.parser")
                return outage_data
        return None
