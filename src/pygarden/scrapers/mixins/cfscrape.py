#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides a CAPTCHA Bypass Mixin."""
import cfscrape
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CfscrapeMixin:
    """
    Group together CFSCRAPE methods.

    This mixin provides CAPTCHA bypass capabilities using cfscrape
    for web scraping operations that may encounter Cloudflare protection.
    """

    def request(self, url, verify=False, **kwargs):
        """
        Fetch data from `url` and return that as a BeautifulSoup object.

        :param url: The URL to request.
        :param verify: Whether to verify SSL certificates (default: False).
        :param kwargs: Additional keyword arguments for cfscrape.
        :return: A BeautifulSoup object containing the parsed HTML.
        """
        scrape = cfscrape.create_scraper(**kwargs)
        scrape.verify = verify
        html_text = scrape.get(url).text
        outage_data = Soup(html_text, "html.parser")
        return outage_data
