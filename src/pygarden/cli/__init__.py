"""
Initialize the CLI module.

This module provides the main CLI interface for pygarden, combining all
available command groups into a single command-line application.

The module provides:
- Main CLI command group with all subcommands
- Integration of database, generation, Python, and Docker commands
- Click-based command-line interface
- Help and usage information

Examples
--------
Run the main CLI::

    $ pygarden --help

Run database commands::

    $ pygarden db --help

Run generation commands::

    $ pygarden gen --help

Run Python project commands::

    $ pygarden py --help

Run Docker commands::

    $ pygarden docker --help

Notes
-----
This module requires the 'click' package to be installed. If not available,
it will display a warning and exit with code 1.
"""

try:
    import click

    from pygarden.cli.docker_cli import docker
    from pygarden.cli.gen_cli import gen_cli
    from pygarden.cli.python_cli import python_cli
except ImportError:
    import sys

    from pygarden.logz import create_logger

    logger = create_logger()
    logger.warn("the [cli] extra must be installed. ")
    sys.exit(1)


@click.group()
def common_cli():
    """
    PyGARDEN (General Application Resource Development Environment Network) CLI.

    This is the main command-line interface for pygarden, providing access
    to various utilities including database operations, file generation,
    Python project setup, and Docker management.

    Examples
    --------
    Get help::

        $ pygarden --help

    List available commands::

        $ pygarden --help

    Run database operations::

        $ pygarden db --help

    Generate test data::

        $ pygarden gen --help

    Set up Python projects::

        $ pygarden py --help

    Manage Docker resources::

        $ pygarden docker --help

    Notes
    -----
    This CLI provides access to all major pygarden functionality through
    organized command groups. Each command group has its own help and
    subcommands for specific operations.
    """
    pass


common_cli.add_command(docker, name="docker")
common_cli.add_command(python_cli, name="py")
common_cli.add_command(gen_cli, name="gen")


if __name__ == "__main__":
    common_cli()
