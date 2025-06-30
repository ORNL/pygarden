#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mix-in class for HTML formatted sites."""
import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HtmlMixin:
    """
    Mix-in for HTML formatted sites.

    This mixin provides HTML parsing capabilities using BeautifulSoup
    for web scraping operations.
    """

    def request(self, url, method="GET", **kwargs):
        """
        Fetch data from `url` and return that as a BeautifulSoup object.

        :param url: The URL of the remote host.
        :param method: One of GET, OPTIONS, HEAD, POST, PUT, PATCH, or DELETE.
        :param kwargs: Optional requests keyword arguments.
        :return: A BeautifulSoup object containing the parsed HTML.
        """
        r = requests.request(method=method.upper(), url=url, **kwargs)

        soup = Soup(r.text, "html.parser")

        return soup
