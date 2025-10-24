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
        Fetch data from `url` and return that in a JSON object.

        :param url: URL of the remote host.
        :param kwargs: Optional requests keyword arguments.
        :returns: JSON response data.
        """
        r = requests.request(method=method, url=url, **kwargs)
        return r.json()
