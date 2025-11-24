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
        return None
    # Handle pandas API changes: error_bad_lines was replaced with on_bad_lines in pandas 1.3+
    read_csv_kwargs = {
        "na_values": [" ", "", "NA", "<NA>"],
        "keep_default_na": True,
        "infer_datetime_format": True,
        "encoding": "utf_8",
    }
    # Only add parse_dates if not overridden in kwargs and if columns might exist
    # Users can override parse_dates in kwargs if needed
    if "parse_dates" not in kwargs:
        read_csv_kwargs["parse_dates"] = ["updated", "access_time"]
    # Use on_bad_lines for newer pandas, fallback to error_bad_lines for older versions
    import inspect
    sig = inspect.signature(pd.read_csv)
    if "on_bad_lines" in sig.parameters:
        read_csv_kwargs["on_bad_lines"] = "skip"
    else:
        read_csv_kwargs["error_bad_lines"] = False
    read_csv_kwargs.update(kwargs)
    try:
        return pd.read_csv(csv, **read_csv_kwargs)
    except ValueError as e:
        # If parse_dates columns don't exist, try again without them
        if "parse_dates" in str(e) and "Missing column" in str(e):
            read_csv_kwargs.pop("parse_dates", None)
            return pd.read_csv(csv, **read_csv_kwargs)
        raise


def glob_csvs(directory, logger=create_logger()):
    """
    Glob for all CSVs in a directory.

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
