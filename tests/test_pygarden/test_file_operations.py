"""Tests for File Operations"""

import pytest
from pygarden.file_operations import (
    append_file,
    create_directory,
    delete_directory,
    delete_file,
    path_exists,
    read_file,
    tree,
    write_file,
)


@pytest.fixture
def setup_file(tmp_path):
    """Create a temporary file for testing."""
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.txt"
    p.write_text("content")
    return p


@pytest.fixture
def setup_directory(tmp_path):
    """Create a temporary directory for testing."""
    d = tmp_path / "subdir"
    d.mkdir()
    return d


@pytest.fixture
def setup_populated_directory(tmp_path):
    """Create a temporary directory for testing."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "subsubdir"
    p.mkdir()
    f = d / "myfile.txt"
    f.write_text("foo")
    return d


def test_path_exists(setup_file):
    """Test that the path exists function works."""
    assert path_exists(setup_file) is True
    assert path_exists("nonexistent_file") is False


def test_create_directory(tmp_path, setup_directory):
    """Test that you can create a directory."""
    assert create_directory(str(setup_directory)) == f"{str(setup_directory)} already exists."
    new_dir = tmp_path / "newdir"
    assert create_directory(str(new_dir)) is True


def test_delete_directory(setup_directory):
    """Test that deleting a directory works as expected."""
    assert delete_directory(str(setup_directory)) == f"{str(setup_directory)} deleted successfully."
    assert delete_directory("nodir") == "nodir does not exist."


def test_tree(setup_populated_directory, setup_file, capsys):
    """Test that the tree command works as expected."""
    print(setup_populated_directory)
    tree(str(setup_populated_directory))
    captured = capsys.readouterr()
    print(captured)
    assert "Directory" in captured.out
    assert "File" in captured.out


def test_read_file(setup_file):
    """Test reading an existing file."""
    assert read_file(str(setup_file)) == "content"
    assert read_file("nonexistent") is None


def test_append_file(setup_file):
    """Test that appending to a file works."""
    content_to_append = " is my favorite content"
    append_file(str(setup_file), content_to_append)
    assert setup_file.read_text() == "content is my favorite content"


def test_write_file(tmp_path):
    """Test that writing a file works."""
    file_path = tmp_path / "write_test.txt"
    write_file(str(file_path), "new content")
    assert file_path.read_text() == "new content"
    json_path = tmp_path / "path.json"
    dictionary = {"key": "value"}
    dict_str = str(dictionary).replace("'", '"')
    json_path.write_text(dict_str)
    assert json_path.read_text() == dict_str
    # TODO @Bhaskar, fix this so that the write_file method works here
    # dict_path = tmp_path / "dict.json"
    # write_file(str(dict_path), dictionary)
    # assert dict_path.read_text() == dict_str
    # write_file('new_dict', dictionary | dictionary2)


def test_delete_file(setup_file):
    """Test deletion of an existing file."""
    assert delete_file(setup_file) == f"File: {str(setup_file)} deleted successfully."
    assert delete_file("nonexistent") == "Error in deleting the file: nonexistent."
