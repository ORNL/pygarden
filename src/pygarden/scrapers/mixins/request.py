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
        Fetch data from `url` and return the response.

        :param url: URL of the remote host.
        :param kwargs: Optional requests keyword arguments.
        :returns: Requests response object.
        """
        return requests.request(url=url, **kwargs)
