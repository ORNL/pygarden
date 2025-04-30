#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a Request Mixin for attaching to Scraping classes."""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestMixin:
    """Group together Request logic into a single Mixin."""

    def request(self, url, **kwargs):
        """
        Fetch data from `url` and return that in a Soup object

        :param url: of the remote host
        :param kwargs: optional requests keyword arguments
        """
        return requests.request(url=url, **kwargs)
