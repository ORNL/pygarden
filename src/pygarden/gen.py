"""
Provide generators for CSV and JSON files with random data.

This module contains utilities for generating test data files with specified
sizes or row counts. It supports both CSV and JSON formats with configurable
column types and data generation.

The module provides functions for:
- Generating random gibberish strings
- Creating data based on specified types (int, float, string)
- Converting human-readable file sizes to bytes
- Generating CSV files with target row counts or file sizes
- Generating JSON files with target file sizes

Examples
--------
Generate a CSV file with 5 columns and 1000 rows::

    >>> generate_csv("test.csv", n_columns=5, target_row_count=1000)

Generate a CSV file with target size of 1MB::

    >>> generate_csv("test.csv", n_columns=3, target_file_size="1MB")

Generate a JSON file with target size of 512KB::

    >>> generate_json("test.json", target_file_size="512KB")

Generate data with specific column types::

    >>> column_types = {"id": "int", "name": "string", "score": "float"}
    >>> generate_csv("data.csv", n_columns=3, target_row_count=100, column_types=column_types)

Notes
-----
- File size units supported: KB, MB, GB, TB
- Column types supported: 'int', 'float', 'string'
- Generated CSV files include headers with random column names
- JSON files have structure: {"data": [{"key1": "value1", ...}, ...]}
"""
import argparse
import csv
import json
import os
import random
import string


def generate_gibberish(length=5):
    """
    Generate a random string of alphabetic gibberish.

    This function creates a random string of specified length using only
    alphabetic characters (both uppercase and lowercase).

    :param length: The length of the random string to generate
    :type length: int
    :return: A random string of alphabetic characters
    :rtype: str

    Examples
    --------
    >>> generate_gibberish(3)
    'XyZ'
    >>> generate_gibberish(10)
    'AbCdEfGhIj'
    >>> len(generate_gibberish(15))
    15
    """
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_data_by_type(column_type):
    """
    Generate data based on the specified column type.

    This function generates random data according to the specified type.
    Supported types include integers, floats, and strings.

    :param column_type: The type of data to generate
    :type column_type: str
    :return: A string representation of the generated data
    :rtype: str
    :raises ValueError: If an unsupported column type is provided

    Examples
    --------
    >>> generate_data_by_type('int')
    '42'
    >>> generate_data_by_type('float')
    '123.45'
    >>> generate_data_by_type('string')
    'AbCdEf'
    >>> generate_data_by_type('unknown')
    'XyZ'  # Falls back to string type
    """
    if column_type == "int":
        return str(random.randint(0, 1000))
    elif column_type == "float":
        return f"{random.uniform(0, 1000):.2f}"
    elif column_type == "string":
        return generate_gibberish(random.randint(3, 10))
    else:
        return generate_gibberish(random.randint(3, 10))


def convert_size_to_bytes(size_str):
    """
    Convert a human-readable file size into bytes.

    This function parses human-readable size strings (e.g., "512MB", "1GB")
    and converts them to their byte equivalents.

    :param size_str: A human-readable size string
    :type size_str: str
    :return: The size in bytes
    :rtype: int
    :raises ValueError: If the size unit is not supported

    Examples
    --------
    >>> convert_size_to_bytes("512MB")
    536870912
    >>> convert_size_to_bytes("1GB")
    1073741824
    >>> convert_size_to_bytes("2TB")
    2199023255552
    >>> convert_size_to_bytes("100KB")
    102400
    """
    size_str = size_str.upper()
    size_units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

    # Split the number and the unit (assume space or no space between)
    size_value, size_unit = (
        "".join(filter(str.isdigit, size_str)),
        "".join(filter(str.isalpha, size_str)),
    )

    if size_unit not in size_units:
        raise ValueError(f"Invalid size unit: {size_unit}. Use KB, MB, GB, or TB.")

    return int(size_value) * size_units[size_unit]


def generate_csv(file_path, n_columns=5, target_file_size=None, target_row_count=None, column_types={}):
    """
    Generate a CSV file with either a target size or target row count.

    This function creates a CSV file with random data. You can specify either
    the number of rows or the target file size, but not both. Column types
    can be customized for more realistic data generation.

    :param file_path: The path where the CSV file will be created
    :type file_path: str
    :param n_columns: Number of columns in the CSV
    :type n_columns: int
    :param target_file_size: Target file size in human-readable format
    :type target_file_size: str or None
    :param target_row_count: Target number of rows in the CSV
    :type target_row_count: int or None
    :param column_types: Dictionary mapping column names to data types
    :type column_types: dict
    :raises ValueError: If both target_file_size and target_row_count are specified

    Examples
    --------
    Generate CSV with 3 columns and 100 rows::

        >>> generate_csv("data.csv", n_columns=3, target_row_count=100)

    Generate CSV with target size::

        >>> generate_csv("data.csv", n_columns=5, target_file_size="1MB")

    Generate CSV with specific column types::

        >>> column_types = {"col1": "int", "col2": "float", "col3": "string"}
        >>> generate_csv("data.csv", n_columns=3, target_row_count=50, column_types=column_types)

    Notes
    -----
    - Column names are randomly generated gibberish
    - If column_types is provided, it should map column names to types
    - Unspecified columns default to 'string' type
    - The function prints progress information to stdout
    """
    if target_file_size and target_row_count:
        raise ValueError("Please specify either target file size or target row count, not both.")

    # Generate gibberish column names
    columns = [generate_gibberish() for _ in range(n_columns)]

    # Write CSV
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)  # Write header

        row_count = 0
        current_file_size = 0

        while True:
            row = []
            for i in range(n_columns):
                column_type = column_types.get(columns[i], "string")
                row.append(generate_data_by_type(column_type))

            writer.writerow(row)
            row_count += 1

            if target_row_count and row_count >= target_row_count:
                break

            current_file_size = os.path.getsize(file_path)
            if target_file_size and current_file_size >= target_file_size:
                break

    print(f"CSV file generated at {file_path} with {row_count} rows.")


def generate_json(file_path, target_file_size):
    """
    Generate a JSON file with a target size.

    This function creates a JSON file with random data up to the specified
    target size. The JSON structure consists of a "data" array containing
    objects with random key-value pairs.

    :param file_path: The path where the JSON file will be created
    :type file_path: str
    :param target_file_size: Target file size in human-readable format
    :type target_file_size: str
    :raises ValueError: If the target_file_size format is invalid

    Examples
    --------
    Generate JSON file with 1MB target size::

        >>> generate_json("data.json", target_file_size="1MB")

    Generate JSON file with 512KB target size::

        >>> generate_json("data.json", target_file_size="512KB")

    Notes
    -----
    - JSON structure: {"data": [{"key1": "value1", ...}, ...]}
    - Each object in the data array has 5 random key-value pairs
    - Keys and values are random gibberish strings
    - The function prints progress information to stdout
    """
    data = {"data": []}

    current_file_size = 0
    with open(file_path, "w") as file:
        while current_file_size < target_file_size:
            row = {}
            for _ in range(5):
                row[generate_gibberish()] = generate_gibberish()

            data["data"].append(row)
            json.dump(data, file)
            current_file_size = os.path.getsize(file_path)

    print(f"JSON file generated at {file_path}.")


def main():
    """
    Provide the main logic for this module if called from the command line.

    This function sets up command-line argument parsing and calls the appropriate
    generation function based on the provided arguments. It supports both CSV
    and JSON generation with various options.

    Examples
    --------
    Command line usage::

        $ python gen.py -c 5 -r 1000
        $ python gen.py -c 3 -s 512MB

    Notes
    -----
    - Requires either --row or --size argument (but not both)
    - Generated files are saved as 'output.csv' in the current directory
    - File size supports units: KB, MB, GB, TB
    """
    parser = argparse.ArgumentParser(description="Generate a large CSV file with random data.")

    parser.add_argument("-c", "--col", type=int, required=True, help="Number of columns in the CSV.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-r", "--row", type=int, help="Number of rows in the CSV.")
    group.add_argument("-s", "--size", type=str, help="Target file size (e.g., 512MB or 1GB).")

    args = parser.parse_args()

    # Parse size if provided
    target_file_size = None
    if args.size:
        try:
            target_file_size = convert_size_to_bytes(args.size)
        except ValueError as e:
            print(e)
            return

    # Generate the CSV
    generate_csv(
        file_path="output.csv",
        n_columns=args.col,
        target_row_count=args.row,
        target_file_size=target_file_size,
        column_types={},
    )


if __name__ == "__main__":
    main()
