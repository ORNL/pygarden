#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide common utilities for checking the environment.

This module provides utility functions for environment variable handling,
type conversion, and environment mocking for testing purposes.
It supports boolean, integer, and string type conversions from environment variables.

**Usage Example:**
    >>> check_environment('DEBUG', default=False)
    False
    >>> boolify('true')
    True
"""
import os
from contextlib import contextmanager

TRUE_SET = {1, "1", "TRUE", "True", "true", True, "yes", "y", "T", "t"}
FALSE_SET = {0, "0", "FALSE", "False", "false", False, "no", "n", "F", "f"}


def boolify(var):
    """
    Convert a variable to a boolean value.

    Check if a variable should be a boolean and return the appropriate boolean value.
    Supports various string representations of boolean values.

    :param var: The variable to check to see if it can be converted to bool.
    :type var: Any
    :return: True or False if the variable can be converted.
    :rtype: bool
    :raises TypeError: If the variable cannot be converted to a boolean.
    :note:
        Case-insensitive string values are supported.
        Numeric values 1 and 0 are supported.
        Common boolean string representations: 'true', 'false', 'yes', 'no', 't', 'f', 'y', 'n'.
    :example:
        >>> boolify('true')
        True
        >>> boolify('FALSE')
        False
        >>> boolify(1)
        True
        >>> boolify('invalid')
        TypeError: unable to evaluate expected boolean value: invalid
    """
    if var in FALSE_SET:
        return False
    if var in TRUE_SET:
        return True
    raise TypeError(f"unable to evaluate expected boolean value: {var}")


def check_environment(env_var, default=None):
    """
    Check availability of an environment variable and return its value.

    Check if an environmental variable or variable is set, and if so,
    return that value, else return the default variable. Supports type
    conversion for boolean and integer defaults.

    :param env_var: The environmental variable to look for.
    :type env_var: str
    :param default: The default value if the environmental variable is not found.
    :type default: Any, optional
    :return: Returns either the value in the environmental variable or the
             default value passed to this function (default of None).
    :rtype: Any
    :note:
        If default is a boolean, attempts to convert the environment variable to boolean.
        If default is an integer, attempts to convert the environment variable to integer.
        Checks both os.environ and global/local variables.
        Sets the environment variable if found in globals/locals.
    :example:
        >>> check_environment('DEBUG', default=False)
        False
        >>> check_environment('PORT', default=8080)
        8080
        >>> check_environment('DATABASE_URL', default='sqlite:///')
        'sqlite:///'
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
    Check availability of multiple environment variables with fallback logic.

    Check if the mod environment variable exists, if so, return that.
    If not, check if the vanilla variable has been specified and return
    that value instead. This is useful for environment-specific configurations.

    :param env_var_multi: The modified environment variable to look for.
    :type env_var_multi: str
    :param multi_value: The value of the modified environmental variable.
    :type multi_value: Any
    :param env_var: The vanilla environment variable to look for.
    :type env_var: str
    :param default: The vanilla environment variable default value.
    :type default: Any, optional
    :return: The value of the environment variable or default.
    :rtype: Any
    :note:
        First checks for the modified environment variable.
        If not found, falls back to the vanilla environment variable.
        Uses check_environment for the actual variable checking.
    :example:
        >>> check_multi_environment('PROD_DATABASE_URL', 'postgresql://', 'DATABASE_URL', 'sqlite:///')
        'sqlite:///'
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
    Mock environment variables for testing purposes.

    This context manager temporarily sets environment variables and
    restores them when the context exits. Useful for testing code
    that depends on environment variables.

    :param temp_vars: A dictionary of the temporary variables in the form of key: value.
    :type temp_vars: dict
    :yield: None
    :rtype: None
    :side effects: Temporarily modifies os.environ, restores original values on exit.
    :note:
        Original environment variable values are preserved and restored.
        If a variable didn't exist originally, it is removed on exit.
        Uses contextlib.contextmanager decorator for automatic cleanup.
    :example:
        >>> with mock_env_vars({'DEBUG': 'true', 'PORT': '9000'}):
        ...     print(os.environ.get('DEBUG'))
        ...     print(os.environ.get('PORT'))
        true
        9000
        >>> print(os.environ.get('DEBUG'))  # Original value restored
        None
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
