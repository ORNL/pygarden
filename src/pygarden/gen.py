"""Provide generators for CSV and JSON files with random data."""

import argparse
import csv
import json
import os
import random
import string


def generate_gibberish(length=5):
    """Generate a random string of alphabetic gibberish.

    :param length: Length of the string to generate.
    :returns: A random string of specified length.
    :rtype: str
    """
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_data_by_type(column_type):
    """Generate data based on the specified column type.

    :param column_type: Type of data to generate ('int', 'float', 'string').
    :returns: Generated data as a string.
    :rtype: str
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
    """Convert a human-readable file size (e.g., 512MB) into bytes.

    :param size_str: Human-readable size string (e.g., '512MB', '1GB').
    :returns: Size in bytes.
    :rtype: int
    :raises ValueError: If the size unit is invalid.
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
    """Generate a CSV file with either a target size or target row count.

    :param file_path: Path where the CSV file will be created.
    :param n_columns: Number of columns in the CSV.
    :param target_file_size: Target file size in bytes.
    :param target_row_count: Target number of rows.
    :param column_types: Dictionary mapping column names to data types.
    :raises ValueError: If both target_file_size and target_row_count are specified.
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
    """Generate a JSON file with a target size.

    :param file_path: Path where the JSON file will be created.
    :param target_file_size: Target file size in bytes.
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
    """Provide the main logic for this module if called from the command line."""
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
