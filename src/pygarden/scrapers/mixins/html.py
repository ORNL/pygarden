#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mix-in class for HTML formatted sites."""
import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HtmlMixin:
    """Mix-in for HTML formatted sites."""

    def request(self, url, method="GET", **kwargs):
        """
        Fetch data from `url` and return that in a Soup object

        :param url: of the remote host
        :param method: one of GET, OPTIONS, HEAD, POST, PUT, PATCH, or DELETE
        :param kwargs: optional requests keyword arguments
        """
        r = requests.request(method=method.upper(), url=url, **kwargs)

        soup = Soup(r.text, "html.parser")

        return soup
