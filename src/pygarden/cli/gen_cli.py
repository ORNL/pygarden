"""Command line arguments for helping generate file sizes."""

import click

from pygarden.gen import convert_size_to_bytes, generate_csv, generate_json


@click.group()
def gen_cli():
    """A CLI to generate large CSV files with random data."""
    pass


@gen_cli.command()
@click.option("--col", "-c", type=int, required=True, help="Number of columns in the CSV.")
@click.option("--row", "-r", type=int, help="Number of rows in the CSV.")
@click.option("--size", "-s", type=str, help="Target file size (e.g., 512MB or 1GB).")
def csv(col, row, size):
    """Generate a CSV file with the specified number of columns and rows or file size.

    :param col: Number of columns in the CSV.
    :param row: Number of rows in the CSV.
    :param size: Target file size (e.g., 512MB or 1GB).
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
    """Create a JSON file with the specified target size.

    :param size: Target file size (e.g., 512MB or 1GB).
    """
    try:
        target_file_size = convert_size_to_bytes(size)
    except ValueError as e:
        click.echo(f"Error: {e}")
        return

    generate_json(file_path="output.json", target_file_size=target_file_size)


if __name__ == "__main__":
    gen_cli()
