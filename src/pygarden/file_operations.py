"""
Provide common utilities for various file operations.

This module provides utility functions for file and directory operations, including
existence checks, creation, deletion, directory walking, and file reading/writing/appending.
It supports both text and JSON files, and uses pathlib for path manipulations.
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

    :param dirc_or_file: Directory or file path to check.
    :type dirc_or_file: str or Path
    :return: True if the path exists, False otherwise.
    :rtype: bool
    :example:
        >>> path_exists('/tmp')
        True
    """
    return Path(dirc_or_file).exists()


def create_directory(dirc=None):
    """
    Create a directory if it doesn't exist.

    :param dirc: Directory path to create.
    :type dirc: str or Path
    :return: True if created, a message if already exists, or None on error.
    :rtype: bool or str or None
    :raises FileNotFoundError: If the parent directory does not exist.
    :example:
        >>> create_directory('mydir')
        True
    :note:
        If the directory already exists, returns a message string.
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
    Delete a directory and its contents (non-recursive).

    :param dirc: Directory path to delete.
    :type dirc: str or Path
    :return: Success message if deleted, or None on error.
    :rtype: str or None
    :raises FileNotFoundError: If the directory does not exist.
    :note:
        Only deletes files and empty subdirectories directly under the given directory.
        Does not recursively delete nested directories with contents.
    :example:
        >>> delete_directory('mydir')
        'mydir deleted successfully.'
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
    Walk a directory and print the contents (non-recursive).

    :param dirc: Directory path to walk.
    :type dirc: str or Path
    :return: None or error message if directory does not exist.
    :rtype: None or str
    :side effects: Prints file and directory names to stdout.
    :example:
        >>> tree('.')
        File: ./file1.txt
        Directory: ./subdir
    :note:
        Only lists files and directories directly under the given directory.
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
    Read a file into a Python object.

    :param file_name: Name or path of the file to read.
    :type file_name: str or Path
    :return: File contents (str for text files, object for JSON files), or None on error.
    :rtype: str or object or None
    :raises FileNotFoundError: If the file does not exist.
    :raises json.JSONDecodeError: If the file is JSON but invalid.
    :example:
        >>> read_file('data.txt')
        'hello world\n'
        >>> read_file('data.json')
        {'foo': 'bar'}
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

    :param file_name: Name or path of the file to append to.
    :type file_name: str or Path
    :param file_data: Data to append to the file (must be a string).
    :type file_data: str
    :return: Success message if appended, or None on error.
    :rtype: str or None
    :raises FileNotFoundError: If the file does not exist.
    :raises TypeError: If file_data is not a string.
    :example:
        >>> append_file('log.txt', 'new line\n')
        'Contents successfully appended to the file'
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
    Write data to a file (overwrites existing content).

    :param file_name: Name or path of the file to write to.
    :type file_name: str or Path
    :param file_data: Data to write to the file. For JSON files, must be a dict.
    :type file_data: str or dict
    :return: None
    :raises FileNotFoundError: If the file cannot be created.
    :raises TypeError: If file_data is not a string for text files, or not a dict for JSON files.
    :side effects: Overwrites the file if it exists.
    :example:
        >>> write_file('output.txt', 'hello')
        >>> write_file('output.json', {'foo': 'bar'})
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

    :param file_name: Name or path of the file to delete.
    :type file_name: str or Path
    :return: Success message if deleted, or error message if not found.
    :rtype: str
    :side effects: Removes the file from the filesystem.
    :example:
        >>> delete_file('old.txt')
        'File: old.txt deleted successfully.'
    """
    if Path(file_name).exists():
        Path(file_name).unlink()
        return f"File: {file_name} deleted successfully."
    return f"Error in deleting the file: {file_name}."
