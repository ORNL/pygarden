#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide common utilities for checking the environment."""

import os
from contextlib import contextmanager

TRUE_SET = {1, "1", "TRUE", "True", "true", True, "yes", "y", "T", "t"}
FALSE_SET = {0, "0", "FALSE", "False", "false", False, "no", "n", "F", "f"}


def boolify(var):
    """
    Check if a variable should be a boolean and return.

    :param var: The variable to check to see if it can be converted to bool.
    :returns: True if the variable represents a truthy value, False if falsy.
    :raises TypeError: If the variable cannot be converted to a boolean.
    """
    if var in FALSE_SET:
        return False
    if var in TRUE_SET:
        return True
    raise TypeError(f"unable to evaluate expected boolean value: {var}")


def check_environment(env_var, default=None):
    """
    Check availability of an environment variable.

    Check if an environmental variable or variable is set, and if so,
    return that value, else return the default variable

    :param env_var: The environmental variable to look for.
    :param default: The default value if the environmental variable is not
                   found.
    :returns: Returns either the value in the environmental variable or the
    default value passed to this function (default of None).
    """
    if env_var in os.environ:
        if isinstance(default, bool):
            return boolify(os.environ[env_var])
        if isinstance(default, int):
            return int(os.environ[env_var])
        return os.environ[env_var]
    # assume if in python environment, it is already a bool or int
    if env_var in globals():
        os.environ[env_var] = str(globals()[env_var])
        return globals()[env_var]
    if env_var in locals():
        os.environ[env_var] = str(locals()[env_var])
        return locals()[env_var]
    if default is not None:
        os.environ[env_var] = str(default)
    return default


def check_multi_environment(env_var_multi, multi_value, env_var, default=None):
    """
    Check availability of multiple environment variables.

    Check if the mod environment variable exists,
    if so, return that. If not, check if the vanilla variable
    has been specified and return that value instead.

    :param env_var_multi: The modified environment variable to look for.
    :param multi_value: The value of the modified environmental variable.
    :param env_var: The vanilla environment variable to look for.
    :param default: The vanilla environment variable default value.
    :returns: The value from the environment variable or default.
    """
    # check for existence of new var, if it exists, set environment
    # return multi value
    if str(env_var_multi) in os.environ:
        return check_environment(env_var_multi, multi_value)
    # set environment for vanilla and return vanilla
    return check_environment(env_var, default)


@contextmanager
def mock_env_vars(temp_vars: dict):
    """
    Mock environment variables.

    :param temp_vars: A dictionary of the temporary variables in the form of key: name.
    """
    # store the original values
    original = {var: os.environ.get(var) for var in temp_vars}
    # apply the temp_vars dict to the environment
    os.environ.update(temp_vars)
    try:
        yield
    finally:
        # restore original values
        for var, value in original.items():
            if value is None:
                del os.environ[var]  # remove the var if not originally set
            else:
                os.environ[var] = value  # restore the original value
