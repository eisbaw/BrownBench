"""Main CLI interface."""

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.option("--config", "-c", type=Path, help="Configuration file")
@click.option("--verbose", "-v", count=True, help="Verbose output (-vv for debug)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
@click.option("--cache-dir", type=Path, help="Cache directory")
@click.pass_context
def cli(
    ctx: click.Context,
    config: Path | None,
    verbose: int,
    quiet: bool,
    cache_dir: Path | None,
) -> None:
    """AI Code Generation Benchmark Suite."""
    # Setup context
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["cache_dir"] = cache_dir or Path.home() / ".cache" / "codegen-bench"

    # Setup logging
    import structlog

    log_level = "DEBUG" if verbose >= 2 else "INFO" if verbose == 1 else "WARNING"
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(log_level))


@cli.command()
@click.option("--tasks", default="core", help="Task set to initialize")
@click.option("--download-projects", is_flag=True, help="Download reference projects")
@click.argument("output_dir", type=Path)
@click.pass_context
def init(
    ctx: click.Context, tasks: str, download_projects: bool, output_dir: Path
) -> None:
    """Initialize benchmark suite."""
    console.print(f"[bold green]Initializing benchmark in {output_dir}[/bold green]")
    console.print(f"Task set: {tasks}")

    if download_projects:
        console.print("[yellow]Downloading reference projects...[/yellow]")

    # Create directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tasks").mkdir(exist_ok=True)
    (output_dir / "projects").mkdir(exist_ok=True)

    console.print("[bold green]Initialization complete![/bold green]")


if __name__ == "__main__":
    cli()
