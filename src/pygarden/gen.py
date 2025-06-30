"""
Provide generators for CSV and JSON files with random data.

This module provides utility functions for generating test data files with
configurable sizes, row counts, and data types. It supports CSV and JSON
formats and can generate files based on target size or row count.

**Usage Example:**
    >>> generate_csv('test.csv', n_columns=3, target_row_count=100)
    >>> generate_json('test.json', target_file_size=1024*1024)  # 1MB
"""
import argparse
import csv
import json
import os
import random
import string


def generate_gibberish(length=5):
    """
    Generate a random string of alphabetic characters.

    :param length: The length of the string to generate (default: 5).
    :type length: int, optional
    :return: A random string of alphabetic characters.
    :rtype: str
    :note:
        Uses only ASCII letters (a-z, A-Z).
        Length must be positive.
    :example:
        >>> generate_gibberish(8)
        'KjMpQrSt'
        >>> generate_gibberish()
        'AbCdE'
    """
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_data_by_type(column_type):
    """
    Generate data based on the specified column type.

    :param column_type: The type of data to generate ('int', 'float', 'string').
    :type column_type: str
    :return: A string representation of the generated data.
    :rtype: str
    :note:
        For 'int': generates random integers between 0 and 1000.
        For 'float': generates random floats between 0 and 1000 with 2 decimal places.
        For 'string': generates random strings between 3 and 10 characters.
        For any other type: defaults to string generation.
    :example:
        >>> generate_data_by_type('int')
        '42'
        >>> generate_data_by_type('float')
        '123.45'
        >>> generate_data_by_type('string')
        'Hello'
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
    Convert a human-readable file size string to bytes.

    :param size_str: A string representing file size with unit (e.g., "512MB", "1GB").
    :type size_str: str
    :return: The size in bytes as an integer.
    :rtype: int
    :raises ValueError: If the size unit is not supported.
    :note:
        Supported units: KB, MB, GB, TB (case-insensitive).
        Units are powers of 1024 (binary).
        Numbers can be separated from units by spaces or no spaces.
    :example:
        >>> convert_size_to_bytes('512MB')
        536870912
        >>> convert_size_to_bytes('1 GB')
        1073741824
        >>> convert_size_to_bytes('2TB')
        2199023255552
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
    Generate a CSV file with random data.

    :param file_path: The path where the CSV file will be created.
    :type file_path: str
    :param n_columns: The number of columns in the CSV (default: 5).
    :type n_columns: int, optional
    :param target_file_size: The target file size in bytes (optional).
    :type target_file_size: int, optional
    :param target_row_count: The target number of rows (optional).
    :type target_row_count: int, optional
    :param column_types: A dictionary mapping column names to data types (default: {}).
    :type column_types: dict, optional
    :raises ValueError: If both target_file_size and target_row_count are specified.
    :side effects: Creates or overwrites the specified file.
    :note:
        Either target_file_size or target_row_count must be specified, but not both.
        Column names are generated randomly using generate_gibberish().
        If column_types is empty, all columns default to 'string' type.
        The file includes a header row with column names.
        Prints a summary message when generation is complete.
    :example:
        >>> generate_csv('data.csv', n_columns=3, target_row_count=100)
        CSV file generated at data.csv with 100 rows.
        >>> generate_csv('large.csv', n_columns=10, target_file_size=1024*1024)
        CSV file generated at large.csv with 1234 rows.
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
    Generate a JSON file with random data.

    :param file_path: The path where the JSON file will be created.
    :type file_path: str
    :param target_file_size: The target file size in bytes.
    :type target_file_size: int
    :side effects: Creates or overwrites the specified file.
    :note:
        The JSON structure is {"data": [array of objects]}.
        Each object has 5 random key-value pairs.
        Keys and values are generated using generate_gibberish().
        The file is written incrementally until the target size is reached.
        Prints a summary message when generation is complete.
    :example:
        >>> generate_json('data.json', 1024*1024)  # 1MB
        JSON file generated at data.json.
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
    Command-line interface for generating test data files.

    This function sets up argument parsing and calls the appropriate generation
    function based on the provided arguments. It provides a CLI for the data
    generation functionality.

    **Command Line Arguments:**
        -c, --col: Number of columns in the CSV (required)
        -r, --row: Number of rows in the CSV (mutually exclusive with --size)
        -s, --size: Target file size (e.g., 512MB or 1GB) (mutually exclusive with --row)

    **Usage Examples:**
        >>> python gen.py -c 5 -r 1000
        >>> python gen.py -c 10 -s 1GB

    :side effects: Creates output.csv file in the current directory.
    :note:
        This function is called when the script is run directly.
        The output file is always named 'output.csv'.
        Size units are case-insensitive and support KB, MB, GB, TB.
        If size parsing fails, the script exits with an error message.
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
