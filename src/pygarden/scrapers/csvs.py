"""Provide generics for dealing with csvs."""

import os
from pathlib import Path

import pandas as pd

from pygarden.logz import create_logger


def get_csv(csv, **kwargs):
    """
    Retrieve a CSV with standard defaults using Pandas.

    Read in a pandas csv with optional arguments.
    :param csv: The csv to import.
    :param kwargs: Additional arguments to pass to pandas.read_csv.
    :returns: pandas.DataFrame
    :rtype: pandas.DataFrame
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
    """Glob for all CSVs in a directory.

    :param directory: Directory to search for CSV files.
    :param logger: Logger instance to use.
    :returns: List of CSV file paths.
    :rtype: list
    """
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
