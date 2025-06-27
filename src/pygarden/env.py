#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide common utilities for checking the environment.

This module provides utilities for working with environment variables,
including checking their availability, converting types, and mocking
them for testing purposes.

The module provides functions for:
- Boolean conversion from various string formats
- Environment variable checking with type conversion
- Multi-environment variable checking with fallbacks
- Environment variable mocking for testing

Examples
--------
Check if an environment variable exists::

    >>> value = check_environment("DATABASE_HOST", "localhost")

Convert boolean environment variable::

    >>> debug_mode = check_environment("DEBUG", False)

Mock environment variables for testing::

    >>> with mock_env_vars({"TEST_VAR": "test_value"}):
    ...     value = check_environment("TEST_VAR")

Check multiple environment variables with fallback::

    >>> host = check_multi_environment("PROD_HOST", "prod-server", "DEV_HOST", "localhost")
"""
import os
from contextlib import contextmanager

TRUE_SET = {1, "1", "TRUE", "True", "true", True, "yes", "y", "T", "t"}
FALSE_SET = {0, "0", "FALSE", "False", "false", False, "no", "n", "F", "f"}


def boolify(var):
    """
    Check if a variable should be a boolean and return.

    Converts various string and numeric representations of boolean values
    to actual boolean values. Supports multiple formats including strings,
    integers, and common boolean representations.

    :param var: The variable to check to see if it can be converted to bool
    :type var: any
    :return: The boolean value of the variable
    :rtype: bool
    :raises TypeError: If the variable cannot be converted to a boolean value

    Examples
    --------
    >>> boolify("True")
    True
    >>> boolify("false")
    False
    >>> boolify(1)
    True
    >>> boolify("yes")
    True
    >>> boolify("no")
    False
    >>> boolify("T")
    True
    >>> boolify("F")
    False
    >>> boolify("invalid")
    Traceback (most recent call last):
    ...
    TypeError: unable to evaluate expected boolean value: invalid
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
    return that value, else return the default variable. The function
    also handles type conversion for boolean and integer defaults.

    :param env_var: The environmental variable to look for
    :type env_var: str
    :param default: The default value if the environmental variable is not found
    :type default: any
    :return: Returns either the value in the environmental variable or the
             default value passed to this function (default of None)
    :rtype: any

    Examples
    --------
    Check for existing environment variable::

        >>> os.environ["TEST_VAR"] = "test_value"
        >>> check_environment("TEST_VAR", "default")
        'test_value'

    Check for non-existing environment variable::

        >>> check_environment("NONEXISTENT", "default")
        'default'

    Check for boolean environment variable::

        >>> os.environ["DEBUG"] = "True"
        >>> check_environment("DEBUG", False)
        True

    Check for integer environment variable::

        >>> os.environ["PORT"] = "8080"
        >>> check_environment("PORT", 3000)
        8080

    Check without default value::

        >>> check_environment("NONEXISTENT")
        None
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

    Check if the mod environment variable exists, if so, return that.
    If not, check if the vanilla variable has been specified and return
    that value instead. This is useful for environment-specific configurations.

    :param env_var_multi: The modified environment variable to look for
    :type env_var_multi: str
    :param multi_value: The value of the modified environmental variable
    :type multi_value: any
    :param env_var: The vanilla environment variable to look for
    :type env_var: str
    :param default: The vanilla environment variable default value
    :type default: any
    :return: The value of the environment variable that exists, or the default
    :rtype: any

    Examples
    --------
    Check for modified environment variable first::

        >>> os.environ["DATABASE_HOST_PROD"] = "prod-server"
        >>> check_multi_environment("DATABASE_HOST_PROD", "prod-server", "DATABASE_HOST", "localhost")
        'prod-server'

    Fall back to vanilla environment variable::

        >>> os.environ["DATABASE_HOST"] = "dev-server"
        >>> check_multi_environment("DATABASE_HOST_PROD", "prod-server", "DATABASE_HOST", "localhost")
        'dev-server'

    Use default when neither exists::

        >>> check_multi_environment("DATABASE_HOST_PROD", "prod-server", "DATABASE_HOST", "localhost")
        'localhost'

    Notes
    -----
    This function is useful for environment-specific configurations where
    you want to check for a production-specific variable first, then fall
    back to a general variable, and finally use a default value.
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

    A context manager that temporarily sets environment variables for testing
    purposes. The original values are restored when the context exits.

    :param temp_vars: A dictionary of the temporary variables in the form of key: value
    :type temp_vars: dict

    Examples
    --------
    Mock environment variables for testing::

        >>> with mock_env_vars({"DATABASE_HOST": "test-server", "DEBUG": "True"}):
        ...     host = check_environment("DATABASE_HOST")
        ...     debug = check_environment("DEBUG", False)
        >>> print(host, debug)
        test-server True

    The environment variables are restored after the context::

        >>> check_environment("DATABASE_HOST", "original")
        'original'

    Mock variables that don't exist::

        >>> with mock_env_vars({"NEW_VAR": "new_value"}):
        ...     value = check_environment("NEW_VAR")
        >>> print(value)
        new_value

    Notes
    -----
    This context manager is particularly useful for unit testing where
    you need to temporarily override environment variables without
    affecting the global environment state.
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
