"""HTML report generation for tournament results with interactive visualizations."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import plotly.graph_objects as go
from jinja2 import Environment, PackageLoader, select_autoescape

from codegen_bench.core.tournament import TournamentResult
from codegen_bench.reporting.visualization import create_pareto_visualization


class HTMLReporter:
    """Generate HTML reports with interactive Plotly visualizations."""

    def __init__(self) -> None:
        """Initialize HTML reporter with Jinja2 environment."""
        self.env = Environment(
            loader=PackageLoader("codegen_bench.reporting", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Add custom filters
        self.env.filters["format_float"] = self._format_float
        self.env.filters["format_cost"] = self._format_cost
        self.env.filters["format_time"] = self._format_time

    def _format_float(self, value: float, decimals: int = 2) -> str:
        """Format float with fixed decimal places."""
        return f"{value:.{decimals}f}"

    def _format_cost(self, value: float) -> str:
        """Format cost in USD."""
        return f"${value:.4f}"

    def _format_time(self, seconds: float) -> str:
        """Format time duration."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}min"
        else:
            return f"{seconds / 3600:.2f}h"

    def generate_report(
        self,
        result: TournamentResult,
        output_path: Path,
        title: str = "Tournament Report",
        include_pareto: bool = True,
    ) -> None:
        """Generate comprehensive HTML report.

        Args:
            result: Tournament results to report
            output_path: Path to save HTML file
            title: Report title
            include_pareto: Whether to include Pareto frontier analysis
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create all visualizations
        charts = self._create_charts(result, include_pareto)

        # Prepare template data
        leaderboard = result.get_leaderboard()
        template_data = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "total_comparisons": result.total_comparisons,
                "total_cost_usd": result.total_cost_usd,
                "duration_seconds": result.duration_seconds,
                "num_duts": len(result.ratings),
                "num_tasks": len(result.tasks_evaluated),
                "num_arenas": len(result.arenas),
                "num_errors": len(result.errors),
            },
            "tasks": result.tasks_evaluated,
            "arenas": result.arenas,
            "leaderboard": [rating.to_dict() for rating in leaderboard],
            "arena_breakdowns": self._compute_arena_breakdowns(result),
            "error_summary": self._compute_error_summary(result),
            "charts": charts,
        }

        # Render template
        template = self.env.get_template("tournament_report.html")
        html_content = template.render(**template_data)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _create_charts(self, result: TournamentResult, include_pareto: bool) -> dict[str, str]:
        """Create all interactive charts as HTML strings.

        Args:
            result: Tournament results
            include_pareto: Whether to include Pareto chart

        Returns:
            Dictionary mapping chart names to HTML strings
        """
        charts = {}

        # 1. ELO Ratings Chart
        charts["elo_ratings"] = self._create_elo_chart(result)

        # 2. Cost Analysis Chart
        charts["cost_analysis"] = self._create_cost_chart(result)

        # 3. Win/Loss/Tie Chart
        charts["wlt_chart"] = self._create_wlt_chart(result)

        # 4. Per-Arena Performance
        charts["arena_performance"] = self._create_arena_performance_chart(result)

        # 5. Pareto Frontier (if requested)
        if include_pareto:
            charts["pareto_frontier"] = self._create_pareto_chart(result)

        return charts

    def _create_elo_chart(self, result: TournamentResult) -> str:
        """Create ELO ratings bar chart with error bars."""
        leaderboard = result.get_leaderboard()

        dut_ids = [r.dut_id for r in leaderboard]
        elos = [r.elo for r in leaderboard]
        std_devs = [r.elo_std for r in leaderboard]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=dut_ids,
                y=elos,
                error_y={"type": "data", "array": std_devs, "visible": True},
                marker={
                    "color": elos,
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "ELO Rating"},
                },
                text=[f"{elo:.0f}±{std:.0f}" for elo, std in zip(elos, std_devs, strict=True)],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>ELO: %{y:.1f}±%{error_y.array:.1f}<br><extra></extra>",
            )
        )

        fig.update_layout(
            title="ELO Ratings with Uncertainty",
            xaxis_title="DUT",
            yaxis_title="ELO Rating",
            template="plotly_white",
            height=500,
            showlegend=False,
        )

        return cast(str, fig.to_html(include_plotlyjs="cdn", div_id="elo_chart"))

    def _create_cost_chart(self, result: TournamentResult) -> str:
        """Create cost analysis chart."""
        leaderboard = result.get_leaderboard()

        dut_ids = [r.dut_id for r in leaderboard]
        costs = [r.total_cost_usd for r in leaderboard]
        times = [r.total_time_seconds for r in leaderboard]

        fig = go.Figure()

        # Cost bars
        fig.add_trace(
            go.Bar(
                name="Cost (USD)",
                x=dut_ids,
                y=costs,
                yaxis="y1",
                marker={"color": "lightblue"},
                text=[f"${c:.3f}" for c in costs],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Cost: $%{y:.4f}<br><extra></extra>",
            )
        )

        # Time line
        fig.add_trace(
            go.Scatter(
                name="Time (seconds)",
                x=dut_ids,
                y=times,
                yaxis="y2",
                mode="lines+markers",
                marker={"color": "red", "size": 10},
                line={"color": "red", "width": 2},
                hovertemplate="<b>%{x}</b><br>Time: %{y:.1f}s<br><extra></extra>",
            )
        )

        fig.update_layout(
            title="Cost and Time Analysis",
            xaxis={"title": "DUT"},
            yaxis={"title": "Cost (USD)", "side": "left", "showgrid": False},
            yaxis2={
                "title": "Time (seconds)",
                "side": "right",
                "overlaying": "y",
                "showgrid": False,
            },
            template="plotly_white",
            height=500,
            hovermode="x unified",
            legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,0.8)"},
        )

        return cast(str, fig.to_html(include_plotlyjs="cdn", div_id="cost_chart"))

    def _create_wlt_chart(self, result: TournamentResult) -> str:
        """Create stacked bar chart for wins/losses/ties."""
        leaderboard = result.get_leaderboard()

        dut_ids = [r.dut_id for r in leaderboard]
        wins = [r.wins for r in leaderboard]
        losses = [r.losses for r in leaderboard]
        ties = [r.ties for r in leaderboard]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                name="Wins",
                x=dut_ids,
                y=wins,
                marker={"color": "green"},
                hovertemplate="<b>%{x}</b><br>Wins: %{y}<br><extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                name="Losses",
                x=dut_ids,
                y=losses,
                marker={"color": "red"},
                hovertemplate="<b>%{x}</b><br>Losses: %{y}<br><extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                name="Ties",
                x=dut_ids,
                y=ties,
                marker={"color": "gray"},
                hovertemplate="<b>%{x}</b><br>Ties: %{y}<br><extra></extra>",
            )
        )

        fig.update_layout(
            title="Win/Loss/Tie Distribution",
            xaxis_title="DUT",
            yaxis_title="Count",
            barmode="stack",
            template="plotly_white",
            height=500,
            legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,0.8)"},
        )

        return cast(str, fig.to_html(include_plotlyjs="cdn", div_id="wlt_chart"))

    def _create_arena_performance_chart(self, result: TournamentResult) -> str:
        """Create heatmap of DUT performance across arenas."""
        # Compute win rates per arena
        arena_performance: dict[str, dict[str, float]] = {}

        for arena in result.arenas:
            arena_performance[arena] = {}
            for dut_id in result.ratings.keys():
                arena_performance[arena][dut_id] = 0.0

        # Count wins per arena
        for dut_a_id, dut_b_id, arena, judgment in result.comparisons:
            winner = judgment.winner
            if winner == "A":
                arena_performance[arena][dut_a_id] += 1.0
            elif winner == "B":
                arena_performance[arena][dut_b_id] += 1.0
            elif winner == "TIE":
                arena_performance[arena][dut_a_id] += 0.5
                arena_performance[arena][dut_b_id] += 0.5

        # Normalize by total comparisons per arena
        for arena in result.arenas:
            total_comparisons = sum(arena_performance[arena].values())
            if total_comparisons > 0:
                for dut_id in arena_performance[arena]:
                    arena_performance[arena][dut_id] /= total_comparisons

        # Create heatmap
        dut_ids = list(result.ratings.keys())
        z_data = [
            [arena_performance[arena][dut_id] for dut_id in dut_ids] for arena in result.arenas
        ]

        fig = go.Figure(
            data=go.Heatmap(
                z=z_data,
                x=dut_ids,
                y=result.arenas,
                colorscale="RdYlGn",
                hoverongaps=False,
                hovertemplate="Arena: %{y}<br>DUT: %{x}<br>Win Rate: %{z:.2%}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Performance Heatmap by Arena",
            xaxis_title="DUT",
            yaxis_title="Arena",
            template="plotly_white",
            height=max(400, len(result.arenas) * 50),
        )

        return cast(str, fig.to_html(include_plotlyjs="cdn", div_id="arena_heatmap"))

    def _create_pareto_chart(self, result: TournamentResult) -> str:
        """Create Pareto frontier visualization."""
        leaderboard = result.get_leaderboard()

        # Extract objectives: ELO (maximize) and Cost (minimize)
        # Convert ELO to negative for minimization in Pareto analysis
        approach_names = [r.dut_id for r in leaderboard]
        objectives = {
            "cost": np.array([r.total_cost_usd for r in leaderboard]),
            "negative_elo": np.array([-r.elo for r in leaderboard]),  # Negate for minimization
        }

        # Create Pareto plot
        fig = create_pareto_visualization(
            approach_names=approach_names,
            objectives=objectives,
            objective_labels={
                "cost": "Cost (USD)",
                "negative_elo": "Negative ELO (lower is better)",
            },
            title="Cost vs. Performance Pareto Frontier",
            show_dominated=True,
        )

        return cast(str, fig.to_html(include_plotlyjs="cdn", div_id="pareto_chart"))

    def _compute_arena_breakdowns(self, result: TournamentResult) -> list[dict[str, Any]]:
        """Compute per-arena statistics.

        Args:
            result: Tournament results

        Returns:
            List of arena breakdown dictionaries
        """
        breakdowns = []

        for arena in result.arenas:
            arena_comparisons = [c for c in result.comparisons if c[2] == arena]

            if not arena_comparisons:
                continue

            # Compute agreement rate
            agreement_rates = [judgment.agreement_rate for _, _, _, judgment in arena_comparisons]
            avg_agreement = sum(agreement_rates) / len(agreement_rates)

            # Count ties
            ties = sum(1 for _, _, _, judgment in arena_comparisons if judgment.winner == "TIE")

            breakdowns.append(
                {
                    "name": arena,
                    "total_comparisons": len(arena_comparisons),
                    "avg_agreement": avg_agreement,
                    "tie_count": ties,
                    "tie_rate": ties / len(arena_comparisons) if arena_comparisons else 0.0,
                }
            )

        return breakdowns

    def _compute_error_summary(self, result: TournamentResult) -> dict[str, Any]:
        """Compute error statistics.

        Args:
            result: Tournament results

        Returns:
            Error summary dictionary
        """
        if not result.errors:
            return {"total": 0, "by_phase": {}, "by_type": {}}

        errors_by_phase: dict[str, int] = {}
        errors_by_type: dict[str, int] = {}

        for error in result.errors:
            # Count by phase
            errors_by_phase[error.phase] = errors_by_phase.get(error.phase, 0) + 1

            # Count by type
            errors_by_type[error.error_type] = errors_by_type.get(error.error_type, 0) + 1

        return {
            "total": len(result.errors),
            "by_phase": errors_by_phase,
            "by_type": errors_by_type,
        }
