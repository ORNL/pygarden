#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide static objects."""

import re
from dataclasses import dataclass


@dataclass
class Colors:
    """Provide a dataclass of colors for pretty printing."""

    BLACK = "\33[30m"
    RED = "\33[31m"
    GREEN = "\33[32m"
    YELLOW = "\33[33m"
    BLUE = "\33[34m"
    VIOLET = "\33[35m"
    BEIGE = "\33[36m"
    WHITE = "\33[37m"
    RESET = "\33[39m"


@dataclass
class UrlRegex:
    """Define a URL Regex."""

    # https://stackoverflow.com/a/48689681/2060081
    HTTP = re.compile(
        r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\." + r"([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
    )
    FTP = re.compile(
        r"((ftp|sftp)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\." + r"([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
    )


@dataclass
class ImageConfig:
    """Static dictionaries and values for OCR of images."""

    PD = {
        "skipinitialspace": True,
        "na_values": [" ", "  ", "na", "nan"],
        "keep_default_na": True,
        "skip_blank_lines": True,
        "parse_dates": True,
        "infer_datetime_format": True,
        "thousands": ",",
        "decimal": ".",
        "error_bad_lines": False,
        "warn_bad_lines": True,
    }
