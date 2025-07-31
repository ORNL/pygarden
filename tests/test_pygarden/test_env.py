"""Create tests for the env module."""

import os

import pytest
from pygarden.env import boolify, check_environment


def test_boolify_true():
    """Test that boolify returns True for all true-like values."""
    true_val = [1, "1", "TRUE", "True", "true", "t", "T", True]

    for val in true_val:
        assert boolify(val) is True, f"Expected true {val} but did not get it."


def test_boolify_false():
    """Test that boolify returns False for all false-like values."""
    false_val = [0, "0", "FALSE", "False", "false", "f", "F", False]
    for val in false_val:
        assert boolify(val) is False, f"Expected False {val} but did not get it."


def test_boolify_raises_typeerror():
    """Test that boolify raises a TypeError for non-boolean values."""
    non_bool_values = ["maybe", 2, [], (), 0.5]
    for val in non_bool_values:
        with pytest.raises(TypeError, match="unable to evaluate expected boolean"):
            boolify(val)


def test_check_environment_existing_variables():
    """Check if the environment variable is set and the correct value is returned."""
    os.environ["TEST_VAR"] = "test_value"
    assert check_environment("TEST_VAR", default="default_value") == "test_value", "Something really bad happened"


def test_check_environment_non_existing_with_default():
    """Check if the environment variable is not set and the default value is returned."""
    if "NON_EXISTING_VAR" in os.environ:
        del os.environ["NON_EXISTING_VAR"]
    assert check_environment("NON_EXISTING_VAR", default="default_value") == "default_value", "Default value is broken"


def test_check_environment_type_conversion_to_bool():
    """Check if the environment variable can be converted to bool."""
    os.environ["BOOL_VAR"] = "True"
    assert check_environment("BOOL_VAR", default=False) is True, "Failed to boolify and check_environment"


# TODO - checks for conversion to int, etc


def check_environment_type_conversion_to_int():
    """Check if the environment variable can be converted to int."""
    os.environ["INT_VAR"] = "0"
    assert check_environment("INT_VAR", default=1) == 0, "Failed to cast to int and check_environment"


def teardown_function(function):
    """Teardown function to remove environment variables after each test."""
    for var in ["TEST_VAR", "BOOL_VAR"]:
        if var in os.environ:
            del os.environ[var]
