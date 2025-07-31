"""Command line arguments for use setting up Python projects."""

import os

import click


@click.group()
def python_cli():
    """Python related commands."""
    pass


@python_cli.command(name="mk-pymodule", help="Create a new Python module directory")
@click.option("--name", "-n", required=True, help="Name of the module")
def mk_pymodule(name):
    """Create a new Python module directory with an __init__.py file.

    :param name: Name of the module to create.
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
    """Create a new __init__.py file."""
    with open("__init__.py", "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("\n")
        f.write('"""Module initialization."""\n')
        f.write("\n")
