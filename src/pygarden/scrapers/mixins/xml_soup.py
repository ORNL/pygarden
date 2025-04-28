#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide an XML Mixin for attatching to Scraping classes."""
import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XML_Soup_Mixin(object):
    """Group together all HTML logic into a single Mixin."""

    def request_html(self, url, method="GET", **kwargs):
        """Return the request as JSON."""
        request_list = {"stream": True, "allow_redirects": True, "verify": False}
        if len(**kwargs) > 0:
            request_list.update(**kwargs)
        return requests.request(method=method.upper(), url=url, **request_list).text

    def request(self, url, method, parser="lxml", **kwargs):
        return Soup(self.request_html(url, method, **kwargs), parser)
