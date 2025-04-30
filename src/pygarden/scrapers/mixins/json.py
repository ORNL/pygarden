#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a JSON Mixin for attaching to Scraping classes."""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JsonMixin:
    """Group together all JSON logic into a single Mixin."""

    def request(self, url, method="GET", **kwargs):
        """
        Fetch data from `url` and return that in a Soup object

        :param url: of the remote host
        :param kwargs: optional requests keyword arguments
        """
        r = requests.request(method=method, url=url, **kwargs)
        return r.json()
