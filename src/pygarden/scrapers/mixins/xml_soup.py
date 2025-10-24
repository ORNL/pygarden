#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide an XML Mixin for attaching to Scraping classes."""

import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XmlSoupMixin(object):
    """Group together all XML logic into a single Mixin."""

    @staticmethod
    def request_html(url, method="GET", **kwargs):
        """Return the request as text.

        :param url: URL to request.
        :param method: HTTP method to use.
        :param kwargs: Additional request parameters.
        :returns: Response text.
        :rtype: str
        """
        request_list = {"stream": True, "allow_redirects": True, "verify": False}
        if len(**kwargs) > 0:
            request_list.update(**kwargs)
        return requests.request(method=method.upper(), url=url, **request_list).text

    def request(self, url, method, parser="lxml", **kwargs):
        """Request the URL and return the parsed content.

        :param url: URL to request.
        :param method: HTTP method to use.
        :param parser: BeautifulSoup parser to use.
        :param kwargs: Additional request parameters.
        :returns: BeautifulSoup object.
        """
        return Soup(self.request_html(url, method, **kwargs), parser)
