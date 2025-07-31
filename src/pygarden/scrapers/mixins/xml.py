#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mix-in for XML formatted sites."""

import requests
import urllib3
from bs4 import BeautifulSoup as Soup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XmlMixin:
    """Mix-in for XML formatted sites."""

    def request(self, url, method="GET", **kwargs):
        """
        Fetch data from `url` and return that in a Soup object.

        :param url: URL of the remote host.
        :param kwargs: Optional requests keyword arguments.
        :returns: BeautifulSoup object.
        """
        r = requests.request(method=method, url=url, **kwargs)

        return Soup(r.text, "lxml")
