#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a Mixin that supports ArcGIS-based sites for attaching to Scraping classes."""

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArcgisMixin:
    """
    Adds support for ArcGIS related websites by standardizing a query

    These ArcGIS parameters specify that we want JSON output, don't want
    geometry, and all the regions that intersect the areas of interest.  It
    will also return *all* the fields. (Think SQL `SELECT *`)

    You may want to override `outFields` to just the fields of interest to
    make returned results easier to analyze.
    You may also want to override `where` to limit the results returned.
    The default `where` is `1=1` which returns all records.
    The default `spatialRel` is `esriSpatialRelIntersects` which returns
    all records that intersect the area of interest.
    The default `returnGeometry` is `false` which means we don't want
    geometry returned.  If you want geometry, set this to `true`.

    This can be modified with the `query_parameters` dictionary.
    For example, to set the `outFields` to just `name` and `id`, you can do:
    ```python
    from pygarden.scrapers.scraper import Scraper
    from pygarden.scrapers.mixins.arcgis import ArcgisMixin
    class MyScraper(ArcgisMixin, Scraper):
        def __init__(self, url):
            super().__init__(url)
            self.query_parameters["params"]["outFields"] = "name,id"
    ```
    """

    query_parameters = {
        "params": {
            "f": "json",
            "where": "1=1",
            "returnGeometry": "false",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
        }
    }

    def request(self, url, **kwargs):
        """
        Fetch data from `url` and return that in a JSON object.

        :param url: URL of the remote host.
        :param kwargs: Optional requests keyword arguments.
        :returns: JSON response data.
        """
        combined_parameters = {**self.query_parameters, **kwargs}
        r = requests.request(url=url, **combined_parameters)
        return r.json()
