"""
Command line arguments for helping generate file sizes.

This module provides Click-based command line interfaces for generating
large CSV and JSON files with random data. It supports both row count
and file size targets.

The module provides:
- CSV file generation with configurable columns and rows/size
- JSON file generation with target file sizes
- Human-readable file size parsing (KB, MB, GB, TB)
- Random data generation for testing purposes

Examples
--------
Generate CSV with 5 columns and 1000 rows::

    $ pygarden gen csv --col 5 --row 1000

Generate CSV with target file size::

    $ pygarden gen csv --col 3 --size 512MB

Generate JSON with target file size::

    $ pygarden gen json --size 1GB

Generate large test files::

    $ pygarden gen csv --col 10 --size 2GB
    $ pygarden gen json --size 500MB

Notes
-----
This module requires the 'click' package and uses the gen module for
actual file generation. Generated files are saved in the current directory.
"""

import click

from pygarden.gen import convert_size_to_bytes, generate_csv, generate_json


@click.group()
def gen_cli():
    """
    A CLI to generate large CSV files with random data.

    This command group provides utilities for generating test data files
    with specified sizes or row counts. It supports both CSV and JSON
    formats with configurable column types and data generation.

    Examples
    --------
    Generate a CSV file::

        $ pygarden gen csv --col 5 --row 1000

    Generate a JSON file::

        $ pygarden gen json --size 512MB

    Generate large test datasets::

        $ pygarden gen csv --col 20 --size 1GB
        $ pygarden gen json --size 2GB

    Notes
    -----
    This command group provides two main commands: 'csv' for generating
    CSV files and 'json' for generating JSON files. Both support various
    size and configuration options.
    """
    pass


@gen_cli.command()
@click.option("--col", "-c", type=int, required=True, help="Number of columns in the CSV.")
@click.option("--row", "-r", type=int, help="Number of rows in the CSV.")
@click.option("--size", "-s", type=str, help="Target file size (e.g., 512MB or 1GB).")
def csv(col, row, size):
    """
    Generate a CSV file with the specified number of columns and rows or file size.

    This command generates a CSV file with random data. You must specify either
    the number of rows or the target file size, but not both.

    :param col: Number of columns in the CSV (required)
    :type col: int
    :param row: Number of rows in the CSV (optional if size is specified)
    :type row: int or None
    :param size: Target file size in human-readable format (optional if row is specified)
    :type size: str or None

    Examples
    --------
    Generate CSV with 3 columns and 500 rows::

        $ pygarden gen csv --col 3 --row 500

    Generate CSV with 5 columns and target size of 1MB::

        $ pygarden gen csv --col 5 --size 1MB

    Generate CSV with 10 columns and 2GB target size::

        $ pygarden gen csv --col 10 --size 2GB

    Use short options::

        $ pygarden gen csv -c 5 -r 1000
        $ pygarden gen csv -c 3 -s 512MB

    Notes
    -----
    - Either --row or --size must be specified, but not both
    - File size supports units: KB, MB, GB, TB
    - Generated file is saved as 'output.csv' in the current directory
    - Column names are randomly generated gibberish
    - Data types are randomly assigned (int, float, string)
    """
    target_file_size = None
    if size:
        try:
            target_file_size = convert_size_to_bytes(size)
        except ValueError as e:
            click.echo(f"Error: {e}")
            return

    generate_csv(
        file_path="output.csv",
        n_columns=col,
        target_row_count=row,
        target_file_size=target_file_size,
        column_types={},  # TODO: add option to specify column types
    )


@gen_cli.command()
@click.option("--size", "-s", type=str, required=True, help="Target file size (e.g., 512MB or 1GB).")
def json(size):
    """
    Create a JSON file with the specified target size.

    This command generates a JSON file with random data up to the specified
    target size.

    :param size: Target file size in human-readable format (required)
    :type size: str

    Examples
    --------
    Generate JSON file with 512MB target size::

        $ pygarden gen json --size 512MB

    Generate JSON file with 1GB target size::

        $ pygarden gen json --size 1GB

    Generate large JSON file::

        $ pygarden gen json --size 5GB

    Use short option::

        $ pygarden gen json -s 2GB

    Notes
    -----
    - File size supports units: KB, MB, GB, TB
    - Generated file is saved as 'output.json' in the current directory
    - JSON structure is: {"data": [{"key1": "value1", ...}, ...]}
    - Each object in the data array has 5 random key-value pairs
    - Keys and values are random gibberish strings
    """
    try:
        target_file_size = convert_size_to_bytes(size)
    except ValueError as e:
        click.echo(f"Error: {e}")
        return

    generate_json(file_path="output.json", target_file_size=target_file_size)


if __name__ == "__main__":
    gen_cli()
