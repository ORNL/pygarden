"""Command-line interface for Trellis generation."""

import asyncio

import click

from pygarden.trellis.config import TrellisConfig
from pygarden.trellis.context import TrellisContext
from pygarden.trellis.generator import TrellisGenerator


@click.group(name="trellis")
def trellis_cli():
    """Generate typed PostgreSQL models and repositories."""


@trellis_cli.command(name="generate")
@click.option("--config", "config_path", default="trellis.toml", show_default=True, type=click.Path(exists=True))
@click.option("--check", is_flag=True, help="Report drift without writing generated files.")
def generate(config_path, check):
    """Generate Trellis artifacts from a live PostgreSQL schema."""

    async def run():
        config = TrellisConfig.load(config_path)
        async with TrellisContext(config) as context:
            connection = getattr(context.database, "connection", context.database)
            return await TrellisGenerator(config).generate(connection, check=check)

    changed = asyncio.run(run())
    if check and changed:
        for path in changed:
            click.echo(str(path))
        raise click.ClickException(f"{len(changed)} generated artifact(s) are out of date")
    click.echo(f"{'Would update' if check else 'Updated'} {len(changed)} generated artifact(s).")
