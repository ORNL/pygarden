#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import warnings

try:
    import bs4
    import cfscrape
    import cloudscraper
    import requests
    import selenium
    import urllib3
    import websocket
except ImportError as e:
    missing_module = str(e).split("No module named ")[-1].replace("'", "")
    warnings.warn(
        f'You should install the extra "scrapers", missing required module: {missing_module}.',
        UserWarning,
    )
