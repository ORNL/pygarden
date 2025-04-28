import os
import pytest
from pygarden.env import boolify, check_environment


def test_boolify_true():
    true_val = [1, "1", "TRUE", "True", "true", 't', 'T', True]

    for val in true_val:
        assert boolify(val) is True, f"Expected true {val} but did not get it."


def test_boolify_false():
    false_val = [0, "0", "FALSE", "False", "false",'f','F', False]
    for val in false_val:
        assert boolify(val) is False, f"Expected False {val} but did not get it."


def test_boolify_raises_typeerror():
    non_bool_values = ["maybe", 2, [], (), 0.5]
    for val in non_bool_values:
        with pytest.raises(TypeError, match="unable to evaluate expected boolean"):
            boolify(val)


def test_check_environment_existing_variables():
    os.environ["TEST_VAR"] = "test_value"
    assert (
        check_environment("TEST_VAR", default="default_value") == "test_value"
    ), "Something really bad happened"


def test_check_environment_non_existing_with_default():
    if "NON_EXISTING_VAR" in os.environ:
        del os.environ["NON_EXISTING_VAR"]
    assert (
        check_environment("NON_EXISTING_VAR", default="default_value")
        == "default_value"
    ), "Default value is broken"


def test_check_environment_type_conversion_to_bool():
    os.environ["BOOL_VAR"] = "True"
    assert (
        check_environment("BOOL_VAR", default=False) is True
    ), "Failed to boolify and check_environment"

# TODO - checks for conversion to int, etc

def check_environment_type_conversion_to_int():
    os.environ["INT_VAR"] = "0"
    assert (
        check_environment("INT_VAR", default=1) == 0
    ), "Failed to cast to int and check_environment"


def teardown_function(function):
    for var in ["TEST_VAR", "BOOL_VAR"]:
        if var in os.environ:
            del os.environ[var] 