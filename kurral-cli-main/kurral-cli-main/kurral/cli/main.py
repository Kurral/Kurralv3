"""
Main CLI entry point for Kurral
"""

import click
from rich.console import Console

from kurral.cli import export, replay, backtest, buckets, memory
from kurral.cli import upload_simple, config_cmd, auth, ab_test

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Kurral - Deterministic LLM Agent Testing & Replay Framework

    Capture, replay, and evaluate LLM agent behaviors with precision.
    """
    pass


# Register subcommands
cli.add_command(auth.auth)
cli.add_command(config_cmd.config)
cli.add_command(ab_test.ab)
cli.add_command(export.export)
cli.add_command(replay.replay)
cli.add_command(backtest.backtest)
cli.add_command(buckets.buckets)
cli.add_command(memory.memory)
cli.add_command(upload_simple.upload)
cli.add_command(upload_simple.download)
cli.add_command(upload_simple.list_r2, name="list-r2")


if __name__ == "__main__":
    cli()

