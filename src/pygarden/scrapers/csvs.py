#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide CSV scraping functionality.

This module provides a CSVScraper class that extends the base Scraper class
to handle CSV data. It includes functionality for reading CSV files from URLs
and parsing them into structured data.

Examples
--------
Create a CSV scraper:
    >>> class MyCSVScraper(CSVScraper):
    ...     def parse(self, data):
    ...         # Parse CSV data
    ...         return data.to_dict('records')

Scrape CSV from URL:
    >>> scraper = MyCSVScraper("https://example.com/data.csv")
    >>> results = scraper.scrape()
"""
import os
from pathlib import Path

import pandas as pd
import requests

from pygarden.logz import create_logger
from pygarden.scrapers.scraper import Scraper


def get_csv(csv, **kwargs):
    """
    Retrieve a CSV with standard defaults using Pandas.

    read in a pandas csv with optional arguments
    :param csv: the csv to import
    :returns: pandas.DataFrame
    """
    logger = create_logger()
    if not os.path.exists(csv):
        logger.error(f"csv file at {csv} does not exist.")
        pass
    return pd.read_csv(
        csv,
        na_values=[" ", "", "NA", "<NA>"],
        keep_default_na=True,
        parse_dates=["updated", "access_time"],
        infer_datetime_format=True,
        encoding="utf_8",
        error_bad_lines=False,
        **kwargs,
    )


def glob_csvs(directory, logger=create_logger()):
    """Globs for all CSVs in a directory."""
    dir_path = Path(directory)

    if not dir_path.exists():
        logger.warning(f"{directory} does not exist")
    elif not dir_path.is_dir():
        logger.warning(f"{directory} is not a directory")
    else:
        logger.info(f"Looking for CSVs in {directory}.")
        csvs = dir_path.glob("*.csv")

        csv_strings = [str(x) for x in csvs]

        if csv_strings == []:
            logger.warning(f"No CSV files found in {directory}.")
            return []

        logger.info(f"Found {len(csv_strings)} CSV files.")
        return csv_strings

    logger.warning(f"No CSV files found in {directory}.")
    return []


class CSVScraper(Scraper):
    """
    Scraper class for CSV data.

    This class extends the base Scraper class to provide CSV-specific
    functionality. It uses pandas to read and parse CSV data from URLs
    or local files.

    Parameters
    ----------
    url : str
        The URL or file path to the CSV data
    **kwargs
        Optional keyword arguments for pandas.read_csv()

    Attributes
    ----------
    url : str
        The URL or file path being scraped
    request_args : dict
        Arguments for pandas.read_csv()

    Examples
    --------
    Create a CSV scraper:
        >>> class MyCSVScraper(CSVScraper):
        ...     def parse(self, data):
        ...         # Filter data
        ...         return data[data['value'] > 10]
        >>> 
        >>> scraper = MyCSVScraper("https://example.com/data.csv")
        >>> results = scraper.scrape()

    Use with custom pandas options:
        >>> scraper = CSVScraper("data.csv", delimiter=';', encoding='utf-8')
        >>> results = scraper.scrape()
    """

    def __init__(self, url: str, **kwargs):
        """
        Initialize the CSV scraper.

        Parameters
        ----------
        url : str
            URL or file path to the CSV data
        **kwargs
            Optional keyword arguments for pandas.read_csv()

        Examples
        --------
        >>> scraper = CSVScraper("https://example.com/data.csv")
        >>> scraper = CSVScraper("local_file.csv", delimiter=';')
        """
        super().__init__(url, **kwargs)

    def request(self, url: str, **kwargs) -> pd.DataFrame:
        """
        Make a request to fetch CSV data.

        This method fetches CSV data from a URL or reads it from a local file
        and returns it as a pandas DataFrame.

        Parameters
        ----------
        url : str
            The URL or file path to fetch CSV data from
        **kwargs
            Additional keyword arguments for pandas.read_csv()

        Returns
        -------
        pandas.DataFrame
            The CSV data as a DataFrame

        Examples
        --------
        >>> scraper = CSVScraper("https://example.com/data.csv")
        >>> df = scraper.request("https://example.com/data.csv")
        >>> print(df.head())
        """
        try:
            # Check if URL is a local file path
            if url.startswith(('http://', 'https://')):
                # Fetch from URL
                response = requests.get(url, **kwargs)
                response.raise_for_status()
                return pd.read_csv(pd.StringIO(response.text), **kwargs)
            else:
                # Read from local file
                return pd.read_csv(url, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to read CSV from {url}: {e}")
            return None

    def parse(self, data: pd.DataFrame) -> any:
        """
        Parse the CSV data.

        This method must be implemented by subclasses to define how
        the CSV DataFrame should be processed.

        Parameters
        ----------
        data : pandas.DataFrame
            The CSV data as a DataFrame

        Returns
        -------
        any
            The parsed data

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses

        Examples
        --------
        Implement in subclass:
            >>> def parse(self, data):
            ...     # Convert to list of dictionaries
            ...     return data.to_dict('records')
            ... 
            ...     # Or filter the data
            ...     return data[data['status'] == 'active']
        """
        raise NotImplementedError
