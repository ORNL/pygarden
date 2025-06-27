"""
Provide common utilities for various file operations.

This module provides utilities for file and directory operations including
creation, deletion, reading, writing, and traversal. It uses the pathlib
package for modern path handling and supports both text and JSON files.

The module provides functions for:
- Path existence checking
- Directory creation and deletion
- Directory tree traversal
- File reading, writing, and appending
- JSON file operations with key/dict updates
- File deletion

Examples
--------
Check if a file exists::

    >>> path_exists("data.txt")
    True

Create a directory::

    >>> create_directory("new_folder")
    True

Read a file::

    >>> content = read_file("data.txt")

Write to a file::

    >>> write_file("output.txt", "Hello World")

Append to a file::

    >>> append_file("log.txt", "New entry\n")

Delete a file::

    >>> delete_file("temp.txt")
    'File: temp.txt deleted successfully.'

Notes
-----
This module uses the pathlib package for modern path handling and provides
a consistent interface for file and directory operations across different
operating systems.
"""
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

    This function uses pathlib to check if a path exists, whether it's
    a file or directory.

    :param dirc_or_file: Directory or file path to check
    :type dirc_or_file: str or Path
    :return: True if the path exists, False otherwise
    :rtype: bool

    Examples
    --------
    >>> path_exists("data.txt")
    True
    >>> path_exists("nonexistent.txt")
    False
    >>> path_exists("/tmp")
    True
    >>> path_exists(Path("current_file.py"))
    True
    """
    return Path(dirc_or_file).exists()


def create_directory(dirc=None):
    """
    Create a directory if it doesn't exist.

    This function creates a directory at the specified path. If the directory
    already exists, it returns a message indicating that. If creation fails,
    it returns None.

    :param dirc: Directory path to create
    :type dirc: str or None
    :return: Success message if directory already exists, True if created successfully, None if failed
    :rtype: str or bool or None

    Examples
    --------
    >>> create_directory("new_folder")
    True
    >>> create_directory("new_folder")
    'new_folder already exists.'
    >>> create_directory("/invalid/path")
    None

    Notes
    -----
    This function uses pathlib.mkdir() which will raise FileNotFoundError
    if the parent directory doesn't exist.
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

    This function recursively deletes a directory and all its contents.
    It first deletes all files and subdirectories, then removes the
    directory itself.

    :param dirc: Directory path to delete
    :type dirc: str or None
    :return: Success message if deleted successfully, None if failed
    :rtype: str or None

    Examples
    --------
    >>> delete_directory("temp_folder")
    'temp_folder deleted successfully.'
    >>> delete_directory("nonexistent")
    'nonexistent does not exist.'
    >>> delete_directory("/system/path")
    None

    Notes
    -----
    This function recursively deletes all contents before removing the
    directory itself. Use with caution as this operation cannot be undone.
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

    This function traverses a directory and prints all files and subdirectories
    found within it. It provides a simple tree-like view of the directory structure.

    :param dirc: Directory path to walk
    :type dirc: str or None
    :return: Error message if directory doesn't exist, None if successful
    :rtype: str or None

    Examples
    --------
    >>> tree("/tmp")
    File: /tmp/file1.txt
    Directory: /tmp/folder1

    >>> tree("nonexistent")
    'nonexistent does not exist.'

    Notes
    -----
    This function prints to stdout and doesn't return the directory structure
    as data. For programmatic access to directory contents, use pathlib directly.
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

    This function reads a file and returns its contents. For JSON files,
    it automatically parses the JSON and returns a dictionary. For text
    files, it returns the raw text content.

    :param file_name: Name of the file to read
    :type file_name: str
    :return: File contents (dict for JSON files, str for text files), None if failed
    :rtype: any or None

    Examples
    --------
    Read a text file::

        >>> content = read_file("data.txt")
        >>> print(content)
        Hello World

    Read a JSON file::

        >>> data = read_file("config.json")
        >>> print(data)
        {'key': 'value'}

    Handle non-existent file::

        >>> read_file("nonexistent.txt")
        File doesn't exist: [Errno 2] No such file or directory: 'nonexistent.txt'
        None

    Handle invalid JSON::

        >>> read_file("invalid.json")
        Invalid JSON file: Expecting value: line 1 column 1 (char 0)
        None
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

    This function appends the specified data to the end of a file. It
    opens the file in append mode and writes the data.

    :param file_name: Name of the file to append to
    :type file_name: str
    :param file_data: Data to append to the file
    :type file_data: str
    :return: Success message if appended successfully, None if failed
    :rtype: str or None

    Examples
    --------
    >>> append_file("log.txt", "New log entry\n")
    'Contents successfully appended to the file'

    Handle non-existent file::

        >>> append_file("nonexistent.txt", "data")
        File doesn't exist: [Errno 2] No such file or directory: 'nonexistent.txt'
        None

    Handle invalid data type::

        >>> append_file("test.txt", 123)
        Error: write() argument must be str, not int, please provide data as string
        None

    Notes
    -----
    This function opens the file in append mode ('a+'), which will create
    the file if it doesn't exist.
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

    This function writes data to a file, overwriting any existing content.
    For JSON files, it updates the existing JSON structure with new data.
    For text files, it writes the data directly.

    :param file_name: Name of the file to write to
    :type file_name: str
    :param file_data: Data to write to the file
    :type file_data: str or dict
    :return: Always returns None
    :rtype: None

    Examples
    --------
    Write text to a file::

        >>> write_file("output.txt", "Hello World")

    Write JSON data::

        >>> data = {"name": "John", "age": 30}
        >>> write_file("config.json", data)

    Update existing JSON file::

        >>> write_file("config.json", {"new_key": "new_value"})

    Handle invalid data type::

        >>> write_file("test.txt", 123)
        Error: write() argument must be str, not int, please provide data as string

    Notes
    -----
    For JSON files, this function will create an empty JSON object if the
    file doesn't exist, then update it with the provided data. For text
    files, it will overwrite any existing content.
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

    This function deletes a file from the filesystem. It checks if the file
    exists before attempting to delete it.

    :param file_name: Name of the file to delete
    :type file_name: str or Path
    :return: Success or error message
    :rtype: str

    Examples
    --------
    >>> delete_file("temp.txt")
    'File: temp.txt deleted successfully.'
    >>> delete_file("nonexistent.txt")
    'Error in deleting the file: nonexistent.txt.'
    >>> delete_file(Path("current_file.py"))
    'File: current_file.py deleted successfully.'

    Notes
    -----
    This function uses pathlib.unlink() to delete files. It will return
    an error message if the file doesn't exist, but won't raise an exception.
    """
    if Path(file_name).exists():
        Path(file_name).unlink()
        return f"File: {file_name} deleted successfully."
    return f"Error in deleting the file: {file_name}."
