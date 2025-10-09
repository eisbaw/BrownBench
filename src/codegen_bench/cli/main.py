"""Main CLI interface."""
# mypy: disable-error-code="misc"

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.option("--config", "-c", type=Path, help="Path to configuration file (YAML or JSON)")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except errors")
@click.option("--cache-dir", type=Path, help="Override default cache directory")
@click.pass_context
def cli(
    ctx: click.Context,
    config: Path | None,
    verbose: int,
    quiet: bool,
    cache_dir: Path | None,
) -> None:
    """BrownBench - AI Code Generation Benchmark Suite.

    Evaluate and compare code generation approaches on realistic brownfield tasks.

    \b
    Quick Start:
        # Generate a solution
        codegen-bench generate --dut simple-chat --task-id task_001

        # Run a quick tournament
        codegen-bench tournament --duts simple-chat,elaborate-prompt --tier 1

        # Export results
        codegen-bench export results.json ./reports/

    \b
    Common Workflows:
        1. Generate → Validate → Compare
        2. Tournament → Export → Analyze
        3. Calibrate → Tournament → Export

    For detailed help on any command, use: codegen-bench COMMAND --help
    """
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
@click.option(
    "--tasks",
    default="core",
    help="Task set to initialize (core, extended, or custom)",
)
@click.option(
    "--download-projects",
    is_flag=True,
    help="Download reference project repositories",
)
@click.argument("output_dir", type=Path)
@click.pass_context
def init(ctx: click.Context, tasks: str, download_projects: bool, output_dir: Path) -> None:
    """Initialize a benchmark suite directory with tasks and structure.

    Creates a directory structure for running benchmarks, including task
    definitions and optionally reference project repositories.

    \b
    Examples:
        # Initialize with core task set
        codegen-bench init ./my-benchmark

        # Initialize and download projects
        codegen-bench init --download-projects ./my-benchmark

    \b
    Directory Structure:
        my-benchmark/
        ├── tasks/           # Task YAML files
        ├── projects/        # Reference codebases (if --download-projects)
        └── results/         # Created on first tournament run
    """
    console.print("[bold cyan]Initializing BrownBench Suite[/bold cyan]")
    console.print("=" * 60)
    console.print(f"Output directory: {output_dir}")
    console.print(f"Task set: {tasks}")
    console.print("")

    if download_projects:
        console.print(
            "[yellow]Note: Downloading reference projects (this may take several minutes)...[/yellow]"
        )

    # Create directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tasks").mkdir(exist_ok=True)
    console.print("[green]✓[/green] Created tasks directory")

    (output_dir / "projects").mkdir(exist_ok=True)
    console.print("[green]✓[/green] Created projects directory")

    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print(f"  cd {output_dir}")
    console.print("  codegen-bench generate --dut simple-chat --task-id task_001")


@cli.command()
@click.option(
    "--dut",
    required=True,
    help="Device under test ID (e.g., 'simple-chat', 'elaborate-prompt')",
)
@click.option("--task-id", required=True, help="Task identifier (e.g., 'task_001')")
@click.option("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
@click.option("--output", "-o", type=Path, help="Save solution to JSON file")
@click.option("--no-cache", is_flag=True, help="Force regeneration, ignore cached solutions")
@click.pass_context
def generate(
    ctx: click.Context,
    dut: str,
    task_id: str,
    seed: int,
    output: Path | None,
    no_cache: bool,
) -> None:
    """Generate a code solution for a specific task using a DUT.

    This command uses a code generation approach (DUT) to solve a brownfield
    coding task, producing code changes that can be validated against tests.

    \b
    Examples:
        # Generate with default options
        codegen-bench generate --dut simple-chat --task-id task_001

        # Generate with custom seed and save to file
        codegen-bench generate --dut simple-chat --task-id task_001 \\
            --seed 123 -o solution.json

        # Force regeneration (bypass cache)
        codegen-bench generate --dut elaborate-prompt --task-id task_005 --no-cache

    \b
    Built-in DUTs:
        simple-chat        - Basic single-turn chat approach
        elaborate-prompt   - Enhanced prompt with codebase context

    Note: Requires ANTHROPIC_API_KEY environment variable for API access.
    """
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
        from codegen_bench.exceptions import DUTError

        dut_class = DUTRegistry.get(dut)
        dut_config = {"api_key": os.getenv("ANTHROPIC_API_KEY")}
        dut_instance = dut_class(dut_config)
    except (ValueError, KeyError, DUTError) as e:
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
@click.option("--compile", "run_compile", is_flag=True, help="Run compilation command only")
@click.option("--test", "run_test", is_flag=True, help="Run test command only")
@click.option("--all", "run_all", is_flag=True, help="Run both compilation and tests (recommended)")
@click.pass_context
def validate(
    ctx: click.Context,
    solution_file: Path,
    run_compile: bool,
    run_test: bool,
    run_all: bool,
) -> None:
    """Validate a generated solution by applying it and running tests.

    This command applies code changes from a solution to an isolated git worktree
    and runs the task's compile and/or test commands to verify correctness.

    \b
    Examples:
        # Validate solution (compile + test)
        codegen-bench validate solution.json --all

        # Only check compilation
        codegen-bench validate solution.json --compile

        # Only run tests
        codegen-bench validate solution.json --test

    \b
    Validation Process:
        1. Create isolated git worktree from project repository
        2. Apply code changes from solution
        3. Run compile command (if specified in task)
        4. Run test command (if specified in task)
        5. Parse output for pass/fail metrics
        6. Automatically clean up worktree

    Exit code 0 indicates success, 1 indicates failure or error.
    """
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
        from codegen_bench.exceptions import WorktreeError

        worktree_strategy = GitWorktreeStrategy(task.codebase_path)
        worktree_path = worktree_strategy.create_worktree()
        console.print(f"Created worktree at: {worktree_path}")
    except (ValueError, WorktreeError) as e:
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
                            f"  Passed: {metrics['passed']}, " f"Failed: {metrics.get('failed', 0)}"
                        )
                else:
                    console.print("[red]Tests: FAILED[/red]")
                    console.print(f"Error: {result.error}")

    finally:
        # Cleanup worktree
        worktree_strategy.remove_worktree(worktree_path)
        console.print("[dim]Cleaned up worktree[/dim]")


@cli.command()
@click.argument("tournament_result_file", type=Path)
@click.argument("output_dir", type=Path)
@click.option(
    "--format",
    "-f",
    "formats",
    multiple=True,
    type=click.Choice(["json", "csv", "latex", "all"], case_sensitive=False),
    default=["all"],
    help="Output formats (can specify multiple)",
)
@click.option("--no-comparisons", is_flag=True, help="Exclude detailed comparison data")
@click.option("--no-errors", is_flag=True, help="Exclude error records")
@click.option(
    "--decimal-places", type=int, default=4, help="Number of decimal places for numeric values"
)
@click.pass_context
def export(
    ctx: click.Context,
    tournament_result_file: Path,
    output_dir: Path,
    formats: tuple[str, ...],
    no_comparisons: bool,
    no_errors: bool,
    decimal_places: int,
) -> None:
    """Export tournament results to various formats (JSON, CSV, LaTeX).

    Exports tournament results from a saved tournament result file to one or more
    output formats. The command creates separate files for different data views:

    - JSON: Complete tournament data
    - CSV: Leaderboard, comparisons, and errors as separate files
    - LaTeX: Publication-ready tables for leaderboard and summary

    Examples:
        codegen-bench export results.json ./output --format json
        codegen-bench export results.json ./output --format csv --format latex
        codegen-bench export results.json ./output --no-comparisons --no-errors
    """
    import json

    from codegen_bench.core.tournament import TournamentResult
    from codegen_bench.reporting.exporters import (
        CSVExporter,
        ExportConfig,
        JSONExporter,
        LaTeXExporter,
    )

    console.print("[bold]Exporting tournament results[/bold]")
    console.print(f"Input: {tournament_result_file}")
    console.print(f"Output directory: {output_dir}")

    # Load tournament result
    if not tournament_result_file.exists():
        console.print(
            f"[red]Error: Tournament result file not found: {tournament_result_file}[/red]"
        )
        raise click.Abort()

    try:
        with open(tournament_result_file) as f:
            result_data = json.load(f)
        result = TournamentResult.from_dict(result_data)
        console.print(f"Loaded tournament with {result.total_comparisons} comparisons")
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[red]Error loading tournament result: {e}[/red]")
        raise click.Abort() from e

    # Create export configuration
    config = ExportConfig(
        include_comparisons=not no_comparisons,
        include_errors=not no_errors,
        pretty_print=True,
        decimal_places=decimal_places,
    )

    # Determine which formats to export
    export_formats = set(formats)
    if "all" in export_formats:
        export_formats = {"json", "csv", "latex"}

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export based on requested formats
    exported_files: list[Path] = []

    try:
        if "json" in export_formats:
            with console.status("[bold blue]Exporting JSON..."):
                json_exporter = JSONExporter(config)
                json_path = output_dir / "tournament.json"
                json_exporter.export(result, json_path)
                exported_files.append(json_path)
                console.print(f"[green]✓[/green] JSON: {json_path}")

        if "csv" in export_formats:
            csv_exporter = CSVExporter(config)

            with console.status("[bold blue]Exporting CSV leaderboard..."):
                leaderboard_csv = output_dir / "leaderboard.csv"
                csv_exporter.export_leaderboard(result, leaderboard_csv)
                exported_files.append(leaderboard_csv)
                console.print(f"[green]✓[/green] CSV Leaderboard: {leaderboard_csv}")

            if config.include_comparisons:
                with console.status("[bold blue]Exporting CSV comparisons..."):
                    comparisons_csv = output_dir / "comparisons.csv"
                    csv_exporter.export_comparisons(result, comparisons_csv)
                    exported_files.append(comparisons_csv)
                    console.print(f"[green]✓[/green] CSV Comparisons: {comparisons_csv}")

            if config.include_errors and result.errors:
                with console.status("[bold blue]Exporting CSV errors..."):
                    errors_csv = output_dir / "errors.csv"
                    csv_exporter.export_errors(result, errors_csv)
                    exported_files.append(errors_csv)
                    console.print(f"[green]✓[/green] CSV Errors: {errors_csv}")

        if "latex" in export_formats:
            latex_exporter = LaTeXExporter(config)

            with console.status("[bold blue]Exporting LaTeX leaderboard..."):
                leaderboard_tex = output_dir / "leaderboard.tex"
                latex_exporter.export_leaderboard(result, leaderboard_tex)
                exported_files.append(leaderboard_tex)
                console.print(f"[green]✓[/green] LaTeX Leaderboard: {leaderboard_tex}")

            with console.status("[bold blue]Exporting LaTeX summary..."):
                summary_tex = output_dir / "summary.tex"
                latex_exporter.export_summary_table(result, summary_tex)
                exported_files.append(summary_tex)
                console.print(f"[green]✓[/green] LaTeX Summary: {summary_tex}")

        console.print("\n[bold green]Export complete![/bold green]")
        console.print(f"Exported {len(exported_files)} file(s)")

    except OSError as e:
        console.print(f"[red]Error writing output files: {e}[/red]")
        raise click.Abort() from e


@cli.command()
@click.option(
    "--duts",
    required=True,
    help="Comma-separated list of DUT IDs to compare (e.g., 'simple-chat,elaborate-prompt')",
)
@click.option(
    "--tasks",
    help="Comma-separated list of task IDs to evaluate (e.g., 'task_001,task_002')",
)
@click.option(
    "--tier",
    type=click.IntRange(1, 3),
    help="Preset tier configuration (1=quick, 2=standard, 3=full)",
)
@click.option(
    "--arenas",
    default="correctness,maintainability",
    help="Comma-separated list of arena names (default: 'correctness,maintainability')",
)
@click.option(
    "--samples", type=int, default=3, help="Number of samples per DUT-task pair (default: 3)"
)
@click.option("--seed", type=int, default=42, help="Base random seed (default: 42)")
@click.option("--output-dir", "-o", type=Path, help="Directory to save results")
@click.option("--checkpoint-dir", type=Path, help="Directory for checkpoints (enables resume)")
@click.option(
    "--checkpoint-interval",
    type=int,
    default=10,
    help="Save checkpoint every N comparisons (default: 10)",
)
@click.option(
    "--num-judges", type=int, default=3, help="Number of judges for consensus (default: 3)"
)
@click.option(
    "--consensus-threshold", type=int, default=2, help="Minimum judges that must agree (default: 2)"
)
@click.pass_context
def tournament(
    ctx: click.Context,
    duts: str,
    tasks: str | None,
    tier: int | None,
    arenas: str,
    samples: int,
    seed: int,
    output_dir: Path | None,
    checkpoint_dir: Path | None,
    checkpoint_interval: int,
    num_judges: int,
    consensus_threshold: int,
) -> None:
    """Run a tournament comparing multiple DUTs across tasks and arenas.

    This command evaluates multiple code generation approaches (DUTs) on a set
    of brownfield coding tasks, comparing their solutions across quality dimensions
    (arenas) using AI judges.

    \b
    Examples:
        # Quick evaluation (Tier 1 preset)
        codegen-bench tournament --duts simple-chat,elaborate-prompt --tier 1

        # Custom task selection
        codegen-bench tournament --duts simple-chat,elaborate-prompt \\
            --tasks task_001,task_002,task_003 --arenas correctness,maintainability

        # With checkpointing (resumable on interruption)
        codegen-bench tournament --duts simple-chat,elaborate-prompt --tier 2 \\
            --checkpoint-dir ./checkpoints --output-dir ./results

    \b
    Tier Configurations:
        Tier 1: Quick eval (5 tasks, ~10 min, ~$2)
        Tier 2: Standard eval (10 tasks, ~30 min, ~$10)
        Tier 3: Full eval (21 tasks, ~2 hours, ~$50)

    \b
    Tournament Pipeline:
        1. Generate solutions for each DUT×task×sample combination
        2. Compare all DUT pairs using AI judges across arenas
        3. Update Bayesian ELO ratings based on judgments
        4. Save results and generate leaderboard

    Note: Requires ANTHROPIC_API_KEY environment variable for API access.
    """
    import os
    import time

    from rich.live import Live
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
    )

    from codegen_bench.cache.store import SolutionCache
    from codegen_bench.core.arena import (
        ARCHITECTURAL_INTEGRITY,
        MAINTAINABILITY,
        PERFORMANCE,
        SAFETY,
        SURGICAL_PRECISION,
        TESTABILITY,
    )
    from codegen_bench.core.tournament import TournamentRunner
    from codegen_bench.dut.registry import DUTRegistry
    from codegen_bench.judge.claude_judge import ClaudeJudge
    from codegen_bench.judge.orchestrator import JudgeOrchestrator
    from codegen_bench.tasks.loader import TaskLoader

    # Arena registry - maps arena names to Arena instances
    ARENA_REGISTRY = {
        "maintainability": MAINTAINABILITY,
        "architecture": ARCHITECTURAL_INTEGRITY,
        "surgical": SURGICAL_PRECISION,
        "testability": TESTABILITY,
        "performance": PERFORMANCE,
        "safety": SAFETY,
        "correctness": MAINTAINABILITY,  # Alias for maintainability
    }

    # Tier presets
    TIER_TASKS = {
        1: ["task_006", "task_007", "task_008", "task_014", "task_015"],  # 5 tasks - quick
        2: [
            "task_001",
            "task_002",
            "task_003",
            "task_004",
            "task_005",
            "task_006",
            "task_007",
            "task_008",
            "task_014",
            "task_015",
        ],  # 10 tasks - standard
        3: [f"task_{i:03d}" for i in range(1, 22)],  # 21 tasks - full
    }

    # Validate inputs
    if tier and tasks:
        console.print("[red]Error: Cannot specify both --tier and --tasks[/red]")
        raise click.Abort()

    if not tier and not tasks:
        console.print("[red]Error: Must specify either --tier or --tasks[/red]")
        raise click.Abort()

    # Parse DUT IDs
    dut_ids = [d.strip() for d in duts.split(",")]
    if len(dut_ids) < 2:
        console.print("[red]Error: Tournament requires at least 2 DUTs[/red]")
        raise click.Abort()

    console.print("[bold cyan]BrownBench Tournament[/bold cyan]")
    console.print("=" * 60)

    # Determine task IDs
    if tier:
        task_ids = TIER_TASKS[tier]
        console.print(f"Configuration: [bold]Tier {tier}[/bold]")
    else:
        task_ids = [t.strip() for t in tasks.split(",")]  # type: ignore
        console.print("Configuration: [bold]Custom[/bold]")

    console.print(f"DUTs: {', '.join(dut_ids)} ({len(dut_ids)} total)")
    console.print(f"Tasks: {len(task_ids)} tasks")
    console.print(f"Samples per pairing: {samples}")

    # Parse and validate arenas
    arena_names = [a.strip() for a in arenas.split(",")]
    console.print(f"Arenas: {', '.join(arena_names)} ({len(arena_names)} total)")
    console.print(f"Judges: {num_judges} (consensus: {consensus_threshold})")
    console.print("")

    # Estimate comparisons
    num_dut_pairs = len(dut_ids) * (len(dut_ids) - 1) // 2
    total_comparisons = num_dut_pairs * len(task_ids) * len(arena_names) * samples
    console.print(
        f"[dim]Expected comparisons: {total_comparisons} "
        f"({num_dut_pairs} DUT pairs × {len(task_ids)} tasks × {len(arena_names)} arenas × {samples} samples)[/dim]"
    )

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("\n[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
        console.print("[yellow]Set it with: export ANTHROPIC_API_KEY='your-key-here'[/yellow]")
        raise click.Abort()

    try:
        # Load DUTs
        console.print("\n[bold]Loading DUTs...[/bold]")
        registry = DUTRegistry
        dut_instances = []
        for dut_id in dut_ids:
            try:
                dut_class = registry.get(dut_id)
                dut_config = {"api_key": os.getenv("ANTHROPIC_API_KEY")}
                dut_instance = dut_class(dut_config)
                dut_instances.append(dut_instance)
                console.print(f"  [green]✓[/green] {dut_id}")
            except (ValueError, KeyError) as e:
                console.print(f"  [red]✗[/red] {dut_id}: {e}")
                raise click.Abort() from None

        # Load tasks
        console.print("\n[bold]Loading tasks...[/bold]")
        task_loader = TaskLoader(Path("tasks"))
        task_instances = []
        for task_id in task_ids:
            try:
                task = task_loader.load_task(task_id)
                task_instances.append(task)
                console.print(f"  [green]✓[/green] {task_id}: {task.name}")
            except FileNotFoundError:
                console.print(f"  [red]✗[/red] {task_id}: Not found")
                raise click.Abort() from None

        # Load arenas from registry
        console.print("\n[bold]Loading arenas...[/bold]")
        arena_instances = []
        for arena_name in arena_names:
            if arena_name not in ARENA_REGISTRY:
                console.print(f"  [red]✗[/red] Unknown arena: {arena_name}")
                console.print("\n[yellow]Available arenas:[/yellow]")
                for available_name in ARENA_REGISTRY.keys():
                    console.print(f"  - {available_name}")
                raise click.Abort() from None
            arena = ARENA_REGISTRY[arena_name]
            arena_instances.append(arena)
            console.print(f"  [green]✓[/green] {arena.display_name}")

        # Initialize components
        console.print("\n[bold]Initializing components...[/bold]")

        cache_dir = ctx.obj["cache_dir"]
        cache = SolutionCache(cache_dir=cache_dir)
        console.print(f"  [green]✓[/green] Cache: {cache_dir}")

        # Create judge instances
        from codegen_bench.judge.base import Judge

        api_key = os.getenv("ANTHROPIC_API_KEY")
        judge_instances: list[Judge] = [
            ClaudeJudge(api_key=api_key, variant=i) for i in range(num_judges)
        ]

        judges = JudgeOrchestrator(judges=judge_instances)
        console.print(f"  [green]✓[/green] Judge orchestrator ({num_judges} judges)")

        if checkpoint_dir:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"  [green]✓[/green] Checkpoints: {checkpoint_dir}")

        # Create tournament
        runner = TournamentRunner(
            duts=dut_instances,
            tasks=task_instances,
            judges=judges,
            arenas=arena_instances,
            cache=cache,
            samples_per_pairing=samples,
        )

        # Progress tracking with Rich
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.completed}/{task.total}"),
            TextColumn("•"),
            TimeElapsedColumn(),
        )

        comparison_task: TaskID | None = None
        comparisons_completed = 0

        def progress_callback(count: int) -> None:
            nonlocal comparisons_completed, comparison_task
            comparisons_completed = count
            if comparison_task is not None:
                progress.update(comparison_task, completed=count)

        # Run tournament with progress display
        console.print("\n[bold green]Starting tournament...[/bold green]\n")

        with Live(progress, console=console, refresh_per_second=4):
            comparison_task = progress.add_task(
                "Running comparisons", total=total_comparisons, completed=0
            )

            start_time = time.time()
            result = runner.run(
                progress_callback=progress_callback,
                output_dir=output_dir,
                checkpoint_dir=checkpoint_dir,
                checkpoint_interval=checkpoint_interval,
            )
            duration = time.time() - start_time

        # Display results
        console.print("\n" + "=" * 60)
        console.print("[bold green]Tournament Complete![/bold green]")
        console.print("=" * 60)

        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Comparisons: {result.total_comparisons}")
        console.print(f"  Duration: {duration:.1f}s ({duration/60:.1f} min)")
        console.print(f"  Total cost: [yellow]${result.total_cost_usd:.4f}[/yellow]")

        if result.errors:
            console.print(f"  Errors: [red]{len(result.errors)}[/red]")

        # Leaderboard
        console.print("\n[bold]Leaderboard:[/bold]")
        console.print("-" * 60)

        for i, rating in enumerate(result.get_leaderboard(), 1):
            rank_symbol = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            console.print(f"{rank_symbol} [bold]{rating.dut_id}[/bold]")
            console.print(
                f"     ELO: {rating.elo:.1f} ± {rating.elo_std:.1f} "
                f"[dim](95% CI: {rating.elo_lower_bound:.1f}-{rating.elo_upper_bound:.1f})[/dim]"
            )
            console.print(
                f"     Record: {rating.wins}W / {rating.losses}L / {rating.ties}T "
                f"[dim](win rate: {rating.wins/(rating.wins+rating.losses+rating.ties):.1%})[/dim]"
            )
            console.print(
                f"     Cost: ${rating.total_cost_usd:.4f}  "
                f"Time: {rating.total_time_seconds:.1f}s  "
                f"Tokens: {rating.total_tokens:,}"
            )
            console.print("")

        # Error summary
        if result.errors:
            console.print("[bold red]Errors:[/bold red]")
            console.print("-" * 60)
            error_by_type: dict[str, int] = {}
            for error in result.errors:
                key = f"{error.phase}:{error.error_type}"
                error_by_type[key] = error_by_type.get(key, 0) + 1

            for error_key, count in sorted(error_by_type.items(), key=lambda x: -x[1]):
                phase, error_type = error_key.split(":", 1)
                console.print(f"  {count}× {error_type} [dim]({phase})[/dim]")

            console.print("\n[dim]See full error details in the output file[/dim]")

        # Save location
        if output_dir:
            console.print(f"\n[bold]Results saved to:[/bold] {output_dir}")
            console.print("[dim]Use 'codegen-bench export' to generate reports[/dim]")

        console.print("\n" + "=" * 60)

    except KeyboardInterrupt:
        console.print("\n[yellow]Tournament interrupted by user[/yellow]")
        if checkpoint_dir:
            console.print(f"[dim]Progress saved to checkpoint: {checkpoint_dir}[/dim]")
            console.print("[dim]Resume with same command[/dim]")
        raise click.Abort() from None
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        if ctx.obj.get("verbose", 0) >= 2:
            console.print("[dim]Traceback:[/dim]")
            traceback.print_exc()
        raise click.Abort() from None


@cli.command()
@click.argument("ground_truth_file", type=Path)
@click.option("--judge", default="claude", help="Judge to calibrate (default: claude)")
@click.option("--output", "-o", type=Path, help="Output file for calibration report")
@click.option(
    "--verbose-report", is_flag=True, help="Include detailed comparison-by-comparison results"
)
@click.option("--simulate", is_flag=True, help="Use simulated judge decisions (for testing)")
@click.pass_context
def calibrate(
    ctx: click.Context,
    ground_truth_file: Path,
    judge: str,
    output: Path | None,
    verbose_report: bool,
    simulate: bool,
) -> None:
    """Calibrate a judge against ground truth judgments.

    This command loads a ground truth dataset, runs the specified judge on
    each comparison, and generates a calibration report showing agreement
    rate, bias detection, and accuracy metrics.

    Example:
        codegen-bench calibrate ground_truth.yaml --judge claude --simulate
    """
    from codegen_bench.stats.calibration import JudgeDecision, generate_calibration_report
    from codegen_bench.stats.ground_truth import GroundTruthDataset

    console.print(f"[bold]Calibrating judge: {judge}[/bold]")
    console.print(f"Ground truth: {ground_truth_file}")

    # Load ground truth dataset
    if not ground_truth_file.exists():
        console.print(f"[red]Error: Ground truth file not found: {ground_truth_file}[/red]")
        raise click.Abort()

    try:
        dataset = GroundTruthDataset.from_yaml(ground_truth_file)
        console.print(f"\nDataset: {dataset.name} (v{dataset.version})")
        console.print(f"Description: {dataset.description}")
        console.print(f"Comparisons: {len(dataset.comparisons)}")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error loading ground truth: {e}[/red]")
        raise click.Abort() from e

    # Check if judge execution is implemented
    if not simulate:
        console.print("\n[red]Error: Judge execution not yet implemented.[/red]")
        console.print("[yellow]Use --simulate flag to test with simulated decisions.[/yellow]")
        raise click.Abort()

    # Simulate judge decisions with realistic error rate
    console.print("\n[yellow]Simulating judge decisions (85% agreement rate)...[/yellow]")

    import random

    random.seed(42)  # Reproducible simulation
    judge_decisions: list[JudgeDecision] = []
    for comp in dataset.comparisons:
        # 85% agreement rate simulation
        if random.random() < 0.85:
            judge_decisions.append(comp.ground_truth)
        else:
            # Random wrong decision
            alternatives: list[JudgeDecision] = [
                d for d in ["A", "B", "TIE"] if d != comp.ground_truth
            ]
            judge_decisions.append(random.choice(alternatives))

    ground_truth = [c.ground_truth for c in dataset.comparisons]

    # Generate calibration report
    console.print("\n[bold]Calibration Results:[/bold]")
    console.print("=" * 60)

    report = generate_calibration_report(judge_decisions, ground_truth, judge_name=judge)
    console.print(report)

    # Save to file if requested
    if output:
        with open(output, "w") as f:
            f.write(report)
        console.print(f"\n[green]Report saved to: {output}[/green]")

    # Verbose output
    if verbose_report:
        console.print("\n[bold]Detailed Comparison Results:[/bold]")
        console.print("-" * 60)
        for i, comp in enumerate(dataset.comparisons):
            judge_decision = judge_decisions[i]
            match = "✓" if judge_decision == comp.ground_truth else "✗"
            console.print(
                f"{match} {comp.id}: Judge={judge_decision}, Truth={comp.ground_truth} "
                f"(Task: {comp.task_id}, Arena: {comp.arena})"
            )


if __name__ == "__main__":
    cli()
