"""Initialize the CLI module."""

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
    """PyGARDEN (General Application Resource Development Environment Network) CLI."""
    pass


common_cli.add_command(docker, name="docker")
common_cli.add_command(python_cli, name="py")
common_cli.add_command(gen_cli, name="gen")


if __name__ == "__main__":
    common_cli()
