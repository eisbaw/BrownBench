"""Main CLI interface."""
# mypy: disable-error-code="misc"

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


@cli.command()
@click.option("--dut", required=True, help="Device under test (approach ID)")
@click.option("--task-id", required=True, help="Task ID to solve")
@click.option("--seed", type=int, default=42, help="Random seed")
@click.option("--output", "-o", type=Path, help="Output file for solution")
@click.option("--no-cache", is_flag=True, help="Force regeneration (ignore cache)")
@click.pass_context
def generate(
    ctx: click.Context,
    dut: str,
    task_id: str,
    seed: int,
    output: Path | None,
    no_cache: bool,
) -> None:
    """Generate solution for a task using specified DUT."""
    import json
    import os

    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.dut.registry import DUTRegistry
    from codegen_bench.tasks.loader import TaskLoader

    console.print(f"[bold]Generating solution with {dut}[/bold]")

    # Load task
    task_loader = TaskLoader(Path("tasks"))
    try:
        task = task_loader.load_task(task_id)
        console.print(f"Task: {task.name}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: Task {task_id} not found[/red]")
        raise click.Abort() from e

    # Get DUT
    try:
        dut_class = DUTRegistry.get(dut)
        dut_config = {"api_key": os.getenv("ANTHROPIC_API_KEY")}
        dut_instance = dut_class(dut_config)
    except (ValueError, KeyError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from e

    # Setup cache
    cache_dir = ctx.obj["cache_dir"]
    cache = SolutionCache(cache_dir)

    # Check cache
    if not no_cache:
        cached = cache.get(dut_instance, task, seed)
        if cached:
            console.print("[yellow]Using cached solution[/yellow]")
            solution = cached
        else:
            with console.status("[bold green]Generating solution..."):
                solution = dut_instance.solve(task, seed)
            cache.put(dut_instance, task, seed, solution)
    else:
        with console.status("[bold green]Generating solution..."):
            solution = dut_instance.solve(task, seed)
        cache.put(dut_instance, task, seed, solution)

    # Display summary
    console.print("\n[bold green]Solution generated![/bold green]")
    console.print(f"Files changed: {len(solution.changed_files)}")
    console.print(f"Tokens: {solution.total_tokens}")
    console.print(f"Cost: ${solution.cost_usd:.4f}")
    console.print(f"Time: {solution.generation_time_seconds:.2f}s")

    # Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(solution.to_dict(), f, indent=2)
        console.print(f"\nSaved to: {output}")


@cli.command()
@click.argument("solution_file", type=Path)
@click.option("--compile", "run_compile", is_flag=True, help="Run compile command")
@click.option("--test", "run_test", is_flag=True, help="Run test command")
@click.option("--all", "run_all", is_flag=True, help="Run all checks")
@click.pass_context
def validate(
    ctx: click.Context,
    solution_file: Path,
    run_compile: bool,
    run_test: bool,
    run_all: bool,
) -> None:
    """Validate a solution by running compile/test commands."""
    import json

    from codegen_bench.core.solution import Solution
    from codegen_bench.tasks.loader import TaskLoader
    from codegen_bench.validation.applicator import SolutionApplicator
    from codegen_bench.validation.executor import ValidationExecutor
    from codegen_bench.validation.worktree import GitWorktreeStrategy

    console.print(f"[bold]Validating solution: {solution_file}[/bold]")

    # Load solution
    with open(solution_file) as f:
        solution_data = json.load(f)
    solution = Solution.from_dict(solution_data)

    # Load task
    task_loader = TaskLoader(Path("tasks"))
    try:
        task = task_loader.load_task(solution.task_id)
    except FileNotFoundError as e:
        console.print(f"[red]Error: Task {solution.task_id} not found[/red]")
        raise click.Abort() from e

    # Create worktree
    if not task.codebase_path.exists():
        console.print(f"[red]Error: Codebase not found at {task.codebase_path}[/red]")
        raise click.Abort()

    try:
        worktree_strategy = GitWorktreeStrategy(task.codebase_path)
        worktree_path = worktree_strategy.create_worktree()
        console.print(f"Created worktree at: {worktree_path}")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from e

    try:
        # Apply solution
        with console.status("[bold blue]Applying solution..."):
            applicator = SolutionApplicator(worktree_path)
            applicator.apply(solution)
        console.print("[green]Solution applied[/green]")

        # Run validation
        executor = ValidationExecutor(worktree_path)

        if run_all or run_compile:
            if task.compile_command:
                with console.status("[bold blue]Compiling..."):
                    result = executor.run_compile(task.compile_command)
                if result.success:
                    console.print("[green]Compilation: PASSED[/green]")
                else:
                    console.print("[red]Compilation: FAILED[/red]")
                    console.print(f"Error: {result.error}")

        if run_all or run_test:
            if task.test_command:
                with console.status("[bold blue]Running tests..."):
                    result = executor.run_tests(task.test_command)
                if result.success:
                    console.print("[green]Tests: PASSED[/green]")
                    # Parse test output
                    metrics = executor.parse_test_output(result.output)
                    if "passed" in metrics:
                        console.print(
                            f"  Passed: {metrics['passed']}, "
                            f"Failed: {metrics.get('failed', 0)}"
                        )
                else:
                    console.print("[red]Tests: FAILED[/red]")
                    console.print(f"Error: {result.error}")

    finally:
        # Cleanup worktree
        worktree_strategy.remove_worktree(worktree_path)
        console.print("[dim]Cleaned up worktree[/dim]")


if __name__ == "__main__":
    cli()
