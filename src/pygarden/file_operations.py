"""Provide common utilities for various file operations."""

import json
from pathlib import Path
from typing import Union

# So, here are the tasks for file operations
# Use Pathlib package
# Create/Delete directory/folder
# Tree command/function to walk a directory
# Read/Append/Delete file -- default format text
# for Json files - use json module
# append a key/dict/etc to the JSON would be nice


def path_exists(dirc_or_file):
    """
    Check if a directory or file exists.

    :param dirc_or_file: Directory or file to check.
    :returns: True if the path exists, False otherwise.
    :rtype: bool
    """
    return Path(dirc_or_file).exists()


def create_directory(dirc=None):
    """
    Create a directory if it doesn't exist.

    :param dirc: Directory to create.
    :returns: Success message or None.
    """
    if dirc is not None:
        try:
            if path_exists(dirc):
                return f"{dirc} already exists."
            else:
                Path(dirc).mkdir()
                return True
        except FileNotFoundError as e:
            print(f"Error: {e}")
    return None


def delete_directory(dirc=None):
    """
    Delete a directory and its contents.

    :param dirc: Directory to delete.
    :returns: Success message or None.
    """
    if dirc is not None:
        try:
            if path_exists(dirc):
                directory_to_delete = Path(dirc)

                for item in directory_to_delete.iterdir():
                    if item.is_file():
                        item.unlink()
                    if item.is_dir():
                        item.rmdir()

                directory_to_delete.rmdir()
                return f"{dirc} deleted successfully."
            else:
                return f"{dirc} does not exist."
        except FileNotFoundError as e:
            print(f"Error: {e}")
    return None


def tree(dirc=None):
    """
    Walk a directory and print the contents.

    :param dirc: Directory to walk.
    :returns: None.
    """
    if dirc is not None:
        try:
            if path_exists(dirc):
                for item in Path(dirc).glob("*"):
                    if item.is_file():
                        print(f"File: {item}")
                    elif item.is_dir():
                        print(f"Directory: {item}")
            else:
                return f"{dirc} does not exist."
        except Exception as e:
            print(f"Error: {e}")
    return None


def read_file(file_name):
    """
    Read a file into a python object.

    :param file_name: Name of the file.
    :returns: File contents or None.
    """
    try:
        with open(f"{file_name}", "r+") as file:
            if Path(file_name).suffix == ".json":
                file_contents = json.load(file)
            else:
                file_contents = file.read()
        return file_contents
    except FileNotFoundError as e:
        print(f"File doesn't exist: {e}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")
    return None


def append_file(file_name, file_data):
    """
    Append data to a file.

    :param file_name: Name of the file.
    :param file_data: Data to append to the file.
    :returns: Success message or None.
    """
    try:
        with open(f"{file_name}", "a+") as file:
            file.write(file_data)
        return "Contents successfully appended to the file"
    except FileNotFoundError as e:
        print(f"File doesn't exist: {e}")
    except TypeError as te:
        print(f"Error: {te}, please provide data as string")
    return None


def write_file(file_name, file_data=""):
    """
    Write data to a file.

    :param file_name: Name of the file.
    :param file_data: Data to write to the file.
    """
    try:
        if Path(file_name).suffix == ".json":
            if not Path(file_name).exists():
                with open(f"{file_name}", "w") as json_file:
                    json_file.write(json.dumps({}))
            with open(f"{file_name}", "r+") as file:
                file_contents = json.load(file)
                file_contents.update(file_data)
                file.seek(0)
                json.dump(file_contents, file, indent=1)
        else:
            with open(file_name, "w") as file:
                file.write(file_data)
    except FileNotFoundError as e:
        print(f"File doesn't exist: {e}")
    except TypeError as te:
        print(f"Error: {te}, please provide data as string")
    return None


def delete_file(file_name: Union[str, Path]):
    """
    Delete a file.

    :param file_name: Name of the file to delete.
    :returns: Success message or error message.
    """
    if Path(file_name).exists():
        Path(file_name).unlink()
        return f"File: {file_name} deleted successfully."
    return f"Error in deleting the file: {file_name}."
