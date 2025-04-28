#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Provide a Mixin that supports ArcGIS-based sites for attaching to Scraping
 classes.
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArcGIS_Mixin:
    """Adds support for ArcGIS related web sites by standardizing a query"""

    # These ArcGIS parameters specify that we want JSON output, don't want
    # geometry, and all the regions that intersect the areas of interest.  It
    # will also return *all* the fields. (Think SQL `SELECT *`)  Note sure what
    # the `where 1=1` means, alas.
    #
    # You may want to override `outFields` to just the fields of interest to
    # make returned results easier to analyze.
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
        """Fetch data from `url` and return that in a Soup object

        :param url: of the remote host
        :param kwargs: optional requests keyword arguments
        """

        combined_parameters = {**self.query_parameters, **kwargs}
        r = requests.request(url=url, **combined_parameters)
        return r.json()
