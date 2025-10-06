"""Terminal reporting for tournament results."""

from rich.console import Console
from rich.table import Table

from codegen_bench.core.tournament import TournamentResult


class TerminalReporter:
    """Generate terminal output for tournament results."""

    def __init__(self, console: Console | None = None):
        """Initialize terminal reporter.

        Args:
            console: Rich console (creates one if not provided)
        """
        self.console = console or Console()

    def display(self, result: TournamentResult) -> None:
        """Display tournament results in terminal.

        Args:
            result: Tournament result to display
        """
        self._print_header(result)
        self._print_leaderboard(result)
        self._print_cost_summary(result)
        self._print_statistics(result)

    def _print_header(self, result: TournamentResult) -> None:
        """Print tournament header."""
        self.console.print()
        self.console.rule("[bold cyan]TOURNAMENT RESULTS", style="cyan")
        self.console.print()
        self.console.print(f"[bold]Tasks:[/bold] {', '.join(result.tasks_evaluated)}")
        self.console.print(f"[bold]Arenas:[/bold] {', '.join(result.arenas)}")
        self.console.print(f"[bold]Total Comparisons:[/bold] {result.total_comparisons}")
        self.console.print(f"[bold]Duration:[/bold] {result.duration_seconds:.1f}s")
        self.console.print()

    def _print_leaderboard(self, result: TournamentResult) -> None:
        """Print ELO leaderboard."""
        self.console.rule("[bold green]ELO LEADERBOARD", style="green")
        self.console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Rank", style="dim", width=6)
        table.add_column("DUT")
        table.add_column("ELO", justify="right")
        table.add_column("95% CI", justify="right")
        table.add_column("W/L/T", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("Tokens", justify="right")

        leaderboard = result.get_leaderboard()

        for rank, dut_rating in enumerate(leaderboard, 1):
            # Format ELO with confidence interval
            elo_str = f"{dut_rating.elo:.0f}"
            ci_str = f"[{dut_rating.elo_lower_bound:.0f}, {dut_rating.elo_upper_bound:.0f}]"

            # Format W/L/T
            wlt_str = f"{dut_rating.wins}/{dut_rating.losses}/{dut_rating.ties}"

            # Format cost
            cost_str = f"${dut_rating.total_cost_usd:.3f}"

            # Format tokens
            tokens_str = f"{dut_rating.total_tokens:,}"

            # Style based on rank
            if rank == 1:
                style = "bold green"
            elif rank == 2:
                style = "bold yellow"
            elif rank == 3:
                style = "bold"
            else:
                style = "dim"

            table.add_row(
                f"#{rank}",
                dut_rating.dut_id,
                elo_str,
                ci_str,
                wlt_str,
                cost_str,
                tokens_str,
                style=style,
            )

        self.console.print(table)
        self.console.print()

    def _print_cost_summary(self, result: TournamentResult) -> None:
        """Print cost summary."""
        self.console.rule("[bold yellow]COST SUMMARY", style="yellow")
        self.console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("DUT")
        table.add_column("Total Cost", justify="right")
        table.add_column("Avg Time/Task", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost/Token", justify="right")

        leaderboard = result.get_leaderboard()
        num_tasks = len(result.tasks_evaluated)

        for dut_rating in leaderboard:
            cost_str = f"${dut_rating.total_cost_usd:.4f}"

            avg_time = dut_rating.total_time_seconds / num_tasks if num_tasks > 0 else 0
            time_str = f"{avg_time:.2f}s"

            tokens_str = f"{dut_rating.total_tokens:,}"

            cost_per_token = (
                dut_rating.total_cost_usd / dut_rating.total_tokens
                if dut_rating.total_tokens > 0
                else 0
            )
            cost_per_token_str = f"${cost_per_token * 1000:.3f}/1K"

            table.add_row(
                dut_rating.dut_id,
                cost_str,
                time_str,
                tokens_str,
                cost_per_token_str,
            )

        self.console.print(table)
        self.console.print()
        self.console.print(f"[bold]Total Tournament Cost:[/bold] ${result.total_cost_usd:.4f}")
        self.console.print()

    def _print_statistics(self, result: TournamentResult) -> None:
        """Print statistical summary."""
        self.console.rule("[bold magenta]STATISTICS", style="magenta")
        self.console.print()

        # Calculate agreement rates from comparisons
        if result.comparisons:
            agreement_rates = [comp[3].agreement_rate for comp in result.comparisons]
            avg_agreement = sum(agreement_rates) / len(agreement_rates)
            self.console.print(f"[bold]Average Judge Agreement:[/bold] {avg_agreement:.1%}")

        # Show ELO spread
        leaderboard = result.get_leaderboard()
        if len(leaderboard) > 1:
            elo_spread = leaderboard[0].elo - leaderboard[-1].elo
            self.console.print(f"[bold]ELO Spread (1st - Last):[/bold] {elo_spread:.0f}")

        # Show uncertainty
        avg_std = sum(r.elo_std for r in leaderboard) / len(leaderboard)
        self.console.print(f"[bold]Average ELO Uncertainty (σ):[/bold] {avg_std:.0f}")

        self.console.print()
