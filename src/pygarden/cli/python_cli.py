"""
Command line arguments for use setting up Python projects.

This module provides Click-based command line interfaces for common Python
project setup tasks, including creating module directories and initialization
files.

The module provides:
- Python module directory creation with __init__.py files
- Standard __init__.py file generation
- Project structure setup utilities
- Click-based command-line interface

Examples
--------
Create a new Python module::

    $ pygarden py mk-pymodule --name mymodule

Create an __init__.py file::

    $ pygarden py mk-init

Create multiple modules::

    $ pygarden py mk-pymodule --name utils
    $ pygarden py mk-pymodule --name models
    $ pygarden py mk-pymodule --name tests

Notes
-----
This module requires the 'click' package and provides utilities for
setting up Python project structures quickly and consistently.
"""
import os

import click


@click.group()
def python_cli():
    """
    Python related commands.

    This command group provides utilities for setting up Python projects
    and modules, including creating directory structures and initialization
    files.

    Examples
    --------
    Create a new module::

        $ pygarden py mk-pymodule --name mymodule

    Create an __init__.py file::

        $ pygarden py mk-init

    Set up a complete project structure::

        $ pygarden py mk-pymodule --name src
        $ pygarden py mk-pymodule --name tests
        $ pygarden py mk-pymodule --name docs

    Notes
    -----
    This command group provides utilities for quickly setting up Python
    project structures with proper initialization files and directory
    organization.
    """
    pass


@python_cli.command(name="mk-pymodule", help="Create a new Python module directory")
@click.option("--name", "-n", required=True, help="Name of the module")
def mk_pymodule(name):
    """
    Create a new Python module directory with an __init__.py file.

    This command creates a new directory with the specified name and
    generates a standard __init__.py file inside it. The command will
    change into the new directory, create the __init__.py file, and
    then return to the original directory.

    :param name: Name of the module directory to create (required)
    :type name: str

    Examples
    --------
    Create a module named 'utils'::

        $ pygarden py mk-pymodule --name utils
        Created directory utils and changed into it.

    Create a module with short option::

        $ pygarden py mk-pymodule -n helpers

    Create nested modules::

        $ pygarden py mk-pymodule --name src
        $ cd src
        $ pygarden py mk-pymodule --name mypackage

    Handle errors gracefully::

        $ pygarden py mk-pymodule --name /invalid/path
        Failed to create directory /invalid/path: [Errno 13] Permission denied

    Notes
    -----
    - The directory will be created in the current working directory
    - An __init__.py file will be automatically created inside the new directory
    - The command will temporarily change into the new directory and then return
    - If the directory already exists, it will not be overwritten
    """
    if name:
        try:
            os.makedirs(name, exist_ok=True)
            os.chdir(name)
            click.echo(f"Created directory {name} and changed into it.")
        except Exception as e:
            click.echo(f"Failed to create directory {name}: {str(e)}")
            return
        ctx = click.get_current_context()
        ctx.invoke(mk_init)
        os.chdir("..")
    else:
        click.echo("Must specify a --name for directory to create")


@python_cli.command(name="mk-init", help="Create a new __init__.py file")
def mk_init():
    """
    Create a new __init__.py file.

    This command creates a standard __init__.py file in the current
    directory with proper Python module initialization headers and
    a basic docstring.

    Examples
    --------
    Create an __init__.py file in the current directory::

        $ pygarden py mk-init

    Create __init__.py files in multiple directories::

        $ cd src
        $ pygarden py mk-init
        $ cd ../tests
        $ pygarden py mk-init

    Notes
    -----
    - The file will be created in the current working directory
    - The file includes standard Python headers and encoding declaration
    - A basic module docstring is included
    - If the file already exists, it will be overwritten
    """
    with open("__init__.py", "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("\n")
        f.write('"""Module initialization."""\n')
        f.write("\n")
