"""Cost estimation command for tournaments."""

import click
from rich.console import Console
from rich.table import Table

from codegen_bench.core.config import PricingConfig


def calculate_tournament_cost(
    num_duts: int,
    num_tasks: int,
    samples_per_pairing: int,
    num_arenas: int,
    use_optimized: bool,
    pricing: PricingConfig,
) -> dict:
    """Calculate detailed tournament cost estimates.

    Args:
        num_duts: Number of DUTs to evaluate
        num_tasks: Number of tasks to run
        samples_per_pairing: Samples per DUT-task pair
        num_arenas: Number of arenas for judging
        use_optimized: Whether using optimized prompts
        pricing: Pricing configuration

    Returns:
        Dictionary with cost breakdown
    """
    # Token estimates based on prompt type
    if use_optimized:
        avg_prompt_tokens = 500  # OptimizedPromptDUT
        avg_output_tokens = 1000
        judge_prompt_tokens = 1200  # OptimizedClaudeJudge
        judge_response_tokens = 100
    else:
        avg_prompt_tokens = 1500  # SimpleChatDUT/ElaboratePromptDUT average
        avg_output_tokens = 1200
        judge_prompt_tokens = 2500  # Standard ClaudeJudge
        judge_response_tokens = 150

    # Generation calculations
    total_generations = num_duts * num_tasks * samples_per_pairing
    gen_input_tokens = total_generations * avg_prompt_tokens
    gen_output_tokens = total_generations * avg_output_tokens

    gen_input_cost = (gen_input_tokens / 1000) * pricing.claude_sonnet_4_5_input_per_1k
    gen_output_cost = (gen_output_tokens / 1000) * pricing.claude_sonnet_4_5_output_per_1k
    generation_cost = gen_input_cost + gen_output_cost

    # Judgment calculations
    num_comparisons = (num_duts * (num_duts - 1)) // 2
    total_judgments = num_comparisons * num_arenas * num_tasks * samples_per_pairing
    judge_input_tokens = total_judgments * judge_prompt_tokens
    judge_output_tokens = total_judgments * judge_response_tokens

    judge_input_cost = (judge_input_tokens / 1000) * pricing.claude_sonnet_4_5_input_per_1k
    judge_output_cost = (judge_output_tokens / 1000) * pricing.claude_sonnet_4_5_output_per_1k
    judgment_cost = judge_input_cost + judge_output_cost

    return {
        "total_generations": total_generations,
        "total_judgments": total_judgments,
        "num_comparisons": num_comparisons,
        "gen_input_tokens": gen_input_tokens,
        "gen_output_tokens": gen_output_tokens,
        "gen_input_cost": gen_input_cost,
        "gen_output_cost": gen_output_cost,
        "generation_cost": generation_cost,
        "judge_input_tokens": judge_input_tokens,
        "judge_output_tokens": judge_output_tokens,
        "judge_input_cost": judge_input_cost,
        "judge_output_cost": judge_output_cost,
        "judgment_cost": judgment_cost,
        "total_cost": generation_cost + judgment_cost,
        "cost_per_dut": (generation_cost + judgment_cost) / num_duts if num_duts > 0 else 0,
        "cost_per_task": (generation_cost + judgment_cost) / num_tasks if num_tasks > 0 else 0,
    }


@click.command()
@click.option(
    "--duts",
    "-d",
    type=int,
    required=True,
    help="Number of DUTs to evaluate",
)
@click.option(
    "--tasks",
    "-t",
    type=int,
    required=True,
    help="Number of tasks to run",
)
@click.option(
    "--samples",
    "-s",
    type=int,
    default=3,
    help="Samples per DUT-task pairing (default: 3)",
)
@click.option(
    "--arenas",
    "-a",
    type=int,
    default=1,
    help="Number of arenas for judging (default: 1)",
)
@click.option(
    "--tier",
    type=click.Choice(["1", "2", "3"]),
    help="Use preset tier configuration (overrides other options)",
)
@click.option(
    "--optimized/--standard",
    default=False,
    help="Use optimized prompts for lower token usage",
)
@click.option(
    "--detailed",
    "-v",
    is_flag=True,
    help="Show detailed breakdown",
)
@click.option(
    "--input-price",
    type=float,
    help="Override input token price per 1K (default: Claude Sonnet)",
)
@click.option(
    "--output-price",
    type=float,
    help="Override output token price per 1K (default: Claude Sonnet)",
)
def estimate(
    duts: int,
    tasks: int,
    samples: int,
    arenas: int,
    tier: str,
    optimized: bool,
    detailed: bool,
    input_price: float,
    output_price: float,
):
    """Estimate tournament costs based on configuration.

    Examples:

        # Quick estimate for 5 DUTs, 20 tasks
        codegen-bench estimate --duts 5 --tasks 20

        # Detailed breakdown with optimized prompts
        codegen-bench estimate --duts 10 --tasks 50 --samples 5 --arenas 3 --optimized -v

        # Use tier preset
        codegen-bench estimate --tier 2

        # Custom pricing
        codegen-bench estimate --duts 3 --tasks 10 --input-price 0.002 --output-price 0.010
    """
    console = Console()

    # Apply tier presets if specified
    if tier:
        tier_configs = {
            "1": {"duts": 3, "tasks": 10, "samples": 2, "arenas": 2},
            "2": {"duts": 5, "tasks": 20, "samples": 3, "arenas": 3},
            "3": {"duts": 10, "tasks": 50, "samples": 5, "arenas": 5},
        }
        config = tier_configs[tier]
        duts = config["duts"]
        tasks = config["tasks"]
        samples = config["samples"]
        arenas = config["arenas"]
        console.print(f"[cyan]Using Tier {tier} configuration[/cyan]")

    # Set up pricing
    pricing = PricingConfig()
    if input_price is not None:
        pricing = PricingConfig(
            claude_sonnet_4_5_input_per_1k=input_price,
            claude_sonnet_4_5_output_per_1k=output_price or pricing.claude_sonnet_4_5_output_per_1k,
        )
    if output_price is not None and input_price is None:
        pricing = PricingConfig(
            claude_sonnet_4_5_input_per_1k=pricing.claude_sonnet_4_5_input_per_1k,
            claude_sonnet_4_5_output_per_1k=output_price,
        )

    # Calculate costs
    result = calculate_tournament_cost(duts, tasks, samples, arenas, optimized, pricing)

    # Display configuration
    console.print("\n[bold cyan]Tournament Configuration[/bold cyan]")
    config_table = Table(show_header=False, box=None)
    config_table.add_column("Parameter", style="bright_blue")
    config_table.add_column("Value", style="white")

    config_table.add_row("DUTs", str(duts))
    config_table.add_row("Tasks", str(tasks))
    config_table.add_row("Samples per pairing", str(samples))
    config_table.add_row("Arenas", str(arenas))
    config_table.add_row("Prompt type", "Optimized" if optimized else "Standard")
    config_table.add_row("Input price (per 1K)", f"${pricing.claude_sonnet_4_5_input_per_1k:.3f}")
    config_table.add_row("Output price (per 1K)", f"${pricing.claude_sonnet_4_5_output_per_1k:.3f}")

    console.print(config_table)

    # Display summary
    console.print("\n[bold green]Cost Estimate[/bold green]")
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Component", style="bright_green")
    summary_table.add_column("Value", style="white", justify="right")

    summary_table.add_row("Generation cost", f"${result['generation_cost']:.2f}")
    summary_table.add_row("Judgment cost", f"${result['judgment_cost']:.2f}")
    summary_table.add_row("[bold]Total cost", f"[bold]${result['total_cost']:.2f}")
    summary_table.add_row("Cost per DUT", f"${result['cost_per_dut']:.2f}")
    summary_table.add_row("Cost per task", f"${result['cost_per_task']:.2f}")

    console.print(summary_table)

    # Display detailed breakdown if requested
    if detailed:
        console.print("\n[bold yellow]Detailed Breakdown[/bold yellow]")

        # Generation details
        gen_table = Table(title="Generation Details", show_header=True)
        gen_table.add_column("Metric", style="yellow")
        gen_table.add_column("Value", justify="right")

        gen_table.add_row("Total generations", f"{result['total_generations']:,}")
        gen_table.add_row("Input tokens", f"{result['gen_input_tokens']:,}")
        gen_table.add_row("Output tokens", f"{result['gen_output_tokens']:,}")
        gen_table.add_row("Input cost", f"${result['gen_input_cost']:.2f}")
        gen_table.add_row("Output cost", f"${result['gen_output_cost']:.2f}")

        console.print(gen_table)

        # Judgment details
        judge_table = Table(title="Judgment Details", show_header=True)
        judge_table.add_column("Metric", style="yellow")
        judge_table.add_column("Value", justify="right")

        judge_table.add_row("DUT comparisons", f"{result['num_comparisons']:,}")
        judge_table.add_row("Total judgments", f"{result['total_judgments']:,}")
        judge_table.add_row("Judge input tokens", f"{result['judge_input_tokens']:,}")
        judge_table.add_row("Judge output tokens", f"{result['judge_output_tokens']:,}")
        judge_table.add_row("Input cost", f"${result['judge_input_cost']:.2f}")
        judge_table.add_row("Output cost", f"${result['judge_output_cost']:.2f}")

        console.print(judge_table)

    # Provide recommendations
    console.print("\n[bold magenta]Recommendations[/bold magenta]")

    # Extract num_comparisons from result
    num_comparisons = result["num_comparisons"]

    if not optimized and result["total_cost"] > 50:
        potential_savings = result["total_cost"] * 0.4  # 40% savings estimate
        console.print(
            f"💡 Use [cyan]--optimized[/cyan] to save approximately "
            f"[green]${potential_savings:.2f}[/green] (40% reduction)"
        )

    if result["total_cost"] > 100:
        console.print("⚠️  Consider using [cyan]BudgetEnforcer[/cyan] to prevent cost overruns")
        console.print("💾 Enable caching to avoid repeated API calls")

    if samples > 5:
        console.print(
            f"📊 High sample count ({samples}) - consider starting with fewer samples for initial tests"
        )

    if num_comparisons > 20:
        console.print(
            f"🔄 Many comparisons ({num_comparisons}) - consider adaptive designs to eliminate poor performers early"
        )

    # Show example command for running tournament
    console.print(f"\n[dim]To run this tournament:[/dim]")
    cmd = f"codegen-bench tournament --duts {duts} --tasks {tasks} --samples {samples}"
    if optimized:
        cmd += " --optimized"
    console.print(f"[dim]{cmd}[/dim]")


if __name__ == "__main__":
    estimate()
