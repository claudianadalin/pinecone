"""Command-line interface for Pinecone bundler."""

import sys
from pathlib import Path

import click

from pinecone import __version__
from pinecone.bundler import bundle, write_bundle
from pinecone.config import load_config
from pinecone.errors import PineconeError


def _print_error(error: PineconeError) -> None:
    """Print a formatted error message."""
    click.echo()
    click.secho("Error: ", fg="red", bold=True, nl=False)
    click.echo(str(error))
    click.echo()


def _print_success(result: "BundleResult") -> None:
    """Print success message."""
    from pinecone.bundler import BundleResult

    click.secho("✓ ", fg="green", bold=True, nl=False)
    click.echo(f"Bundled {result.modules_count} module(s) → {result.output_path}")


@click.group()
@click.version_option(version=__version__, prog_name="pinecone")
def cli() -> None:
    """Pinecone - PineScript Bundler

    Bundle multi-file PineScript projects into single TradingView-compatible output.
    """
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False),
    help="Path to pine.config.json",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Watch for file changes and rebuild",
)
@click.option(
    "--copy",
    is_flag=True,
    help="Copy output to clipboard",
)
def build(config: str | None, watch: bool, copy: bool) -> None:
    """Bundle PineScript files into a single output."""
    try:
        # Load config
        config_path = Path(config) if config else None
        cfg = load_config(config_path)

        if watch:
            # Watch mode
            _run_watch_mode(cfg, copy)
        else:
            # Single build
            _run_build(cfg, copy)

    except PineconeError as e:
        _print_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        sys.exit(0)


def _run_build(cfg: "PineconeConfig", copy: bool) -> None:
    """Run a single build."""
    from pinecone.config import PineconeConfig

    result = bundle(cfg)
    write_bundle(result)
    _print_success(result)

    if copy:
        _copy_to_clipboard(result.output)


def _copy_to_clipboard(content: str) -> None:
    """Copy content to clipboard."""
    try:
        import pyperclip

        pyperclip.copy(content)
        click.secho("✓ ", fg="green", bold=True, nl=False)
        click.echo("Copied to clipboard")
    except Exception as e:
        click.secho("⚠ ", fg="yellow", bold=True, nl=False)
        click.echo(f"Could not copy to clipboard: {e}")


def _run_watch_mode(cfg: "PineconeConfig", copy: bool) -> None:
    """Run in watch mode."""
    from pinecone.watcher import watch_and_rebuild

    click.echo(f"Watching for changes in {cfg.src_dir}...")
    click.echo("Press Ctrl+C to stop.\n")

    def on_success(result: "BundleResult") -> None:
        from pinecone.bundler import BundleResult

        _print_success(result)
        if copy:
            _copy_to_clipboard(result.output)

    def on_error(error: Exception) -> None:
        if isinstance(error, PineconeError):
            _print_error(error)
        else:
            click.secho("Error: ", fg="red", bold=True, nl=False)
            click.echo(str(error))

    # Initial build
    try:
        result = bundle(cfg)
        write_bundle(result)
        on_success(result)
    except PineconeError as e:
        on_error(e)

    # Start watching
    watch_and_rebuild(cfg, on_success, on_error)


if __name__ == "__main__":
    cli()
