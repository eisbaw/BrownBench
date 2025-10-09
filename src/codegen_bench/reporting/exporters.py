"""Export tournament results to various formats (JSON, CSV, LaTeX)."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codegen_bench.core.tournament import TournamentResult


@dataclass
class ExportConfig:
    """Configuration for tournament result exports.

    Attributes:
        include_comparisons: Include detailed comparison data
        include_errors: Include error records
        pretty_print: Use pretty printing for JSON
        decimal_places: Number of decimal places for numeric values
    """

    include_comparisons: bool = True
    include_errors: bool = True
    pretty_print: bool = True
    decimal_places: int = 4


class JSONExporter:
    """Export tournament results to JSON format."""

    def __init__(self, config: ExportConfig | None = None):
        """Initialize JSON exporter.

        Args:
            config: Export configuration (uses defaults if None)
        """
        self.config = config or ExportConfig()

    def export(self, result: TournamentResult, output_path: Path) -> None:
        """Export tournament results to JSON file.

        Args:
            result: Tournament results to export
            output_path: Path to output JSON file

        Raises:
            OSError: If file cannot be written
        """
        data = result.to_dict()

        # Filter based on config
        if not self.config.include_comparisons:
            data.pop("comparisons", None)
        if not self.config.include_errors:
            data.pop("errors", None)

        # Write JSON file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            if self.config.pretty_print:
                json.dump(data, f, indent=2, sort_keys=False)
            else:
                json.dump(data, f)

    def export_to_string(self, result: TournamentResult) -> str:
        """Export tournament results to JSON string.

        Args:
            result: Tournament results to export

        Returns:
            JSON string representation
        """
        data = result.to_dict()

        # Filter based on config
        if not self.config.include_comparisons:
            data.pop("comparisons", None)
        if not self.config.include_errors:
            data.pop("errors", None)

        if self.config.pretty_print:
            return json.dumps(data, indent=2, sort_keys=False)
        return json.dumps(data)


class CSVExporter:
    """Export tournament results to CSV format for analysis."""

    def __init__(self, config: ExportConfig | None = None):
        """Initialize CSV exporter.

        Args:
            config: Export configuration (uses defaults if None)
        """
        self.config = config or ExportConfig()

    def export_leaderboard(self, result: TournamentResult, output_path: Path) -> None:
        """Export leaderboard to CSV file.

        Args:
            result: Tournament results to export
            output_path: Path to output CSV file

        Raises:
            OSError: If file cannot be written
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        leaderboard = result.get_leaderboard()
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "rank",
                    "dut_id",
                    "elo",
                    "elo_std",
                    "elo_lower_bound",
                    "elo_upper_bound",
                    "wins",
                    "losses",
                    "ties",
                    "total_cost_usd",
                    "total_time_seconds",
                    "total_tokens",
                ],
            )
            writer.writeheader()

            for rank, rating in enumerate(leaderboard, start=1):
                row = rating.to_dict()
                row["rank"] = rank
                # Format numeric values with fixed decimal places
                for key in ["elo", "elo_std", "elo_lower_bound", "elo_upper_bound", "total_cost_usd", "total_time_seconds"]:
                    if key in row:
                        row[key] = f"{row[key]:.{self.config.decimal_places}f}"
                writer.writerow(row)

    def export_comparisons(self, result: TournamentResult, output_path: Path) -> None:
        """Export detailed comparisons to CSV file.

        Args:
            result: Tournament results to export
            output_path: Path to output CSV file

        Raises:
            OSError: If file cannot be written
        """
        if not self.config.include_comparisons:
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "dut_a",
                    "dut_b",
                    "arena",
                    "winner",
                    "agreement_rate",
                    "confidence",
                ],
            )
            writer.writeheader()

            for dut_a, dut_b, arena, judgment in result.comparisons:
                row = {
                    "dut_a": dut_a,
                    "dut_b": dut_b,
                    "arena": arena,
                    "winner": judgment.winner,
                    "agreement_rate": round(judgment.agreement_rate, self.config.decimal_places),
                    "confidence": round(judgment.confidence, self.config.decimal_places),
                }
                writer.writerow(row)

    def export_errors(self, result: TournamentResult, output_path: Path) -> None:
        """Export error records to CSV file.

        Args:
            result: Tournament results to export
            output_path: Path to output CSV file

        Raises:
            OSError: If file cannot be written
        """
        if not self.config.include_errors or not result.errors:
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "phase",
                    "dut_id",
                    "task_id",
                    "arena",
                    "error_type",
                    "error_message",
                    "is_retryable",
                ],
            )
            writer.writeheader()

            for error in result.errors:
                row = error.to_dict()
                # Remove error_context as it's complex for CSV
                row.pop("error_context", None)
                writer.writerow(row)


class LaTeXExporter:
    """Export tournament results to LaTeX table format."""

    def __init__(self, config: ExportConfig | None = None):
        """Initialize LaTeX exporter.

        Args:
            config: Export configuration (uses defaults if None)
        """
        self.config = config or ExportConfig()

    def export_leaderboard(self, result: TournamentResult, output_path: Path) -> None:
        """Export leaderboard to LaTeX table file.

        Args:
            result: Tournament results to export
            output_path: Path to output .tex file

        Raises:
            OSError: If file cannot be written
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        leaderboard = result.get_leaderboard()
        latex_content = self._generate_leaderboard_table(leaderboard)

        with open(output_path, "w") as f:
            f.write(latex_content)

    def export_leaderboard_to_string(self, result: TournamentResult) -> str:
        """Export leaderboard to LaTeX table string.

        Args:
            result: Tournament results to export

        Returns:
            LaTeX table as string
        """
        leaderboard = result.get_leaderboard()
        return self._generate_leaderboard_table(leaderboard)

    def _generate_leaderboard_table(self, leaderboard: list[Any]) -> str:
        """Generate LaTeX table from leaderboard data.

        Args:
            leaderboard: List of DUTRating objects

        Returns:
            LaTeX table as string
        """
        # Start table
        lines = [
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Tournament Leaderboard Results}",
            "\\label{tab:tournament_leaderboard}",
            "\\begin{tabular}{rlrrrrrrr}",
            "\\toprule",
            "Rank & DUT ID & ELO & $\\pm\\sigma$ & W & L & T & Cost (\\$) & Time (s) \\\\",
            "\\midrule",
        ]

        # Add data rows
        for rank, rating in enumerate(leaderboard, start=1):
            elo = round(rating.elo, 1)
            std = round(rating.elo_std, 1)
            cost = round(rating.total_cost_usd, self.config.decimal_places)
            time = round(rating.total_time_seconds, 1)

            # Escape underscores in DUT ID for LaTeX
            dut_id_escaped = rating.dut_id.replace("_", "\\_")

            line = (
                f"{rank} & {dut_id_escaped} & {elo} & {std} & "
                f"{rating.wins} & {rating.losses} & {rating.ties} & "
                f"{cost} & {time} \\\\"
            )
            lines.append(line)

        # End table
        lines.extend([
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ])

        return "\n".join(lines)

    def export_summary_table(self, result: TournamentResult, output_path: Path) -> None:
        """Export tournament summary to LaTeX table file.

        Args:
            result: Tournament results to export
            output_path: Path to output .tex file

        Raises:
            OSError: If file cannot be written
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        latex_content = self._generate_summary_table(result)

        with open(output_path, "w") as f:
            f.write(latex_content)

    def _generate_summary_table(self, result: TournamentResult) -> str:
        """Generate LaTeX summary table from tournament results.

        Args:
            result: Tournament results

        Returns:
            LaTeX table as string
        """
        duration_hours = result.duration_seconds / 3600
        cost = result.total_cost_usd

        lines = [
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Tournament Summary Statistics}",
            "\\label{tab:tournament_summary}",
            "\\begin{tabular}{lr}",
            "\\toprule",
            "Metric & Value \\\\",
            "\\midrule",
            f"Total Comparisons & {result.total_comparisons} \\\\",
            f"DUTs Evaluated & {len(result.ratings)} \\\\",
            f"Tasks & {len(result.tasks_evaluated)} \\\\",
            f"Arenas & {len(result.arenas)} \\\\",
            f"Total Cost & \\${cost:.{self.config.decimal_places}f} \\\\",
            f"Duration & {duration_hours:.2f} hours \\\\",
        ]

        if result.errors:
            lines.append(f"Errors & {len(result.errors)} \\\\")

        lines.extend([
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ])

        return "\n".join(lines)


def export_all_formats(
    result: TournamentResult,
    output_dir: Path,
    config: ExportConfig | None = None,
) -> dict[str, Path]:
    """Export tournament results to all supported formats.

    Args:
        result: Tournament results to export
        output_dir: Directory for output files
        config: Export configuration (uses defaults if None)

    Returns:
        Dictionary mapping format name to output file path
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    config = config or ExportConfig()

    exported_files: dict[str, Path] = {}

    # JSON export
    json_exporter = JSONExporter(config)
    json_path = output_dir / "tournament.json"
    json_exporter.export(result, json_path)
    exported_files["json"] = json_path

    # CSV exports
    csv_exporter = CSVExporter(config)

    leaderboard_csv = output_dir / "leaderboard.csv"
    csv_exporter.export_leaderboard(result, leaderboard_csv)
    exported_files["csv_leaderboard"] = leaderboard_csv

    if config.include_comparisons:
        comparisons_csv = output_dir / "comparisons.csv"
        csv_exporter.export_comparisons(result, comparisons_csv)
        exported_files["csv_comparisons"] = comparisons_csv

    if config.include_errors and result.errors:
        errors_csv = output_dir / "errors.csv"
        csv_exporter.export_errors(result, errors_csv)
        exported_files["csv_errors"] = errors_csv

    # LaTeX exports
    latex_exporter = LaTeXExporter(config)

    leaderboard_tex = output_dir / "leaderboard.tex"
    latex_exporter.export_leaderboard(result, leaderboard_tex)
    exported_files["latex_leaderboard"] = leaderboard_tex

    summary_tex = output_dir / "summary.tex"
    latex_exporter.export_summary_table(result, summary_tex)
    exported_files["latex_summary"] = summary_tex

    return exported_files
