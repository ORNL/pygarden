#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide an HTML Mixin for attaching to Scraping classes."""
import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HtmlSoupMixin(object):
    """
    Group together all HTML logic into a single Mixin.

    This mixin provides HTML parsing capabilities using BeautifulSoup
    for web scraping operations.
    """

    def request_html(self, url, method="get", **kwargs):
        """
        Return the request.

        :param url: The URL to request.
        :param method: The HTTP method to use (default: "get").
        :param kwargs: Additional keyword arguments for the request.
        :return: The response text content.
        """
        request_list = {"stream": True, "allow_redirects": True, "verify": False}
        if len(**kwargs) > 0:
            request_list.update(**kwargs)
        return requests.request(method=method.upper(), url=url, **request_list).text

    def request(self, url, method, parser="html.parser", **kwargs):
        """
        Return a soup'd object.

        :param url: The URL to request.
        :param method: The HTTP method to use.
        :param parser: The parser to use for BeautifulSoup (default: "html.parser").
        :param kwargs: Additional keyword arguments for the request.
        :return: A BeautifulSoup object containing the parsed HTML.
        """
        return Soup(self.request_html(url, method, **kwargs), parser)
