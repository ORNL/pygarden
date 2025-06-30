#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mix-in for XML formatted sites."""
import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XmlMixin:
    """
    Mix-in for XML formatted sites.

    This mixin provides XML parsing capabilities using BeautifulSoup
    for web scraping operations.
    """

    def request(self, url, method="GET", **kwargs):
        """
        Fetch data from `url` and return that as a BeautifulSoup object.

        :param url: The URL of the remote host.
        :param method: The HTTP method to use (default: "GET").
        :param kwargs: Optional requests keyword arguments.
        :return: A BeautifulSoup object containing the parsed XML.
        """
        r = requests.request(method=method, url=url, **kwargs)

        return Soup(r.text, "lxml")
