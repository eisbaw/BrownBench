"""Tests for tournament result exporters."""

import csv
import json
from pathlib import Path

import pytest

from codegen_bench.core.judgment import JudgeVote, JudgmentResult
from codegen_bench.core.tournament import DUTRating, ErrorRecord, TournamentResult
from codegen_bench.reporting.exporters import (
    CSVExporter,
    ExportConfig,
    JSONExporter,
    LaTeXExporter,
    export_all_formats,
)
from codegen_bench.stats.ratings.bayesian_elo import BayesianELO


@pytest.fixture
def sample_result() -> TournamentResult:
    """Create sample tournament result for testing."""
    ratings = {
        "dut1": DUTRating(
            dut_id="dut1",
            rating=BayesianELO(prior_mean=1600, prior_std=50),
            total_cost_usd=10.5,
            total_time_seconds=120.0,
            total_tokens=5000,
        ),
        "dut2": DUTRating(
            dut_id="dut2",
            rating=BayesianELO(prior_mean=1500, prior_std=60),
            total_cost_usd=8.3,
            total_time_seconds=100.0,
            total_tokens=4000,
        ),
    }

    # Add some comparison history to ratings
    votes = [
        JudgeVote(vote="A", reasoning="Better implementation", confidence=0.9),
        JudgeVote(vote="A", reasoning="Cleaner code", confidence=0.85),
        JudgeVote(vote="B", reasoning="More concise", confidence=0.75),
    ]
    comparison = (
        "dut1",
        "dut2",
        "correctness",
        JudgmentResult(
            winner="A",
            votes=votes,
            agreement_rate=0.85,
            confidence=0.9,
        ),
    )
    ratings["dut1"]._comparisons.append(comparison)
    ratings["dut2"]._comparisons.append(comparison)

    result = TournamentResult(
        ratings=ratings,
        comparisons=[comparison],
        tasks_evaluated=["task1", "task2"],
        arenas=["correctness", "readability"],
        total_comparisons=1,
        total_cost_usd=18.8,
        start_time=1000.0,
        end_time=1220.0,
        errors=[
            ErrorRecord(
                timestamp="2025-01-01T00:00:00",
                phase="solution_generation",
                dut_id="dut1",
                task_id="task1",
                arena="correctness",
                error_type="APIError",
                error_message="Rate limit exceeded",
                is_retryable=True,
                error_context={"retry_count": 3},
            )
        ],
    )

    return result


class TestJSONExporter:
    """Tests for JSON exporter."""

    def test_export_to_file(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting to JSON file."""
        exporter = JSONExporter()
        output_path = tmp_path / "result.json"

        exporter.export(sample_result, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)

        assert "tournament_metadata" in data
        assert "leaderboard" in data
        assert "comparisons" in data
        assert "errors" in data
        assert data["tournament_metadata"]["total_cost_usd"] == 18.8
        assert len(data["leaderboard"]) == 2

    def test_export_without_comparisons(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test exporting without comparisons."""
        config = ExportConfig(include_comparisons=False)
        exporter = JSONExporter(config)
        output_path = tmp_path / "result.json"

        exporter.export(sample_result, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert "comparisons" not in data
        assert "leaderboard" in data

    def test_export_without_errors(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting without errors."""
        config = ExportConfig(include_errors=False)
        exporter = JSONExporter(config)
        output_path = tmp_path / "result.json"

        exporter.export(sample_result, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert "errors" not in data
        assert "leaderboard" in data

    def test_export_to_string(self, sample_result: TournamentResult) -> None:
        """Test exporting to JSON string."""
        exporter = JSONExporter()
        json_str = exporter.export_to_string(sample_result)

        data = json.loads(json_str)
        assert "tournament_metadata" in data
        assert "leaderboard" in data

    def test_export_compact_format(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting in compact format (no pretty print)."""
        config = ExportConfig(pretty_print=False)
        exporter = JSONExporter(config)
        output_path = tmp_path / "result.json"

        exporter.export(sample_result, output_path)

        with open(output_path) as f:
            content = f.read()

        # Compact format should have no indentation
        assert "\n  " not in content or content.count("\n") < 5  # Very few newlines

    def test_export_creates_parent_directory(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test that export creates parent directory if needed."""
        output_path = tmp_path / "subdir" / "result.json"
        exporter = JSONExporter()

        exporter.export(sample_result, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()


class TestCSVExporter:
    """Tests for CSV exporter."""

    def test_export_leaderboard(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting leaderboard to CSV."""
        exporter = CSVExporter()
        output_path = tmp_path / "leaderboard.csv"

        exporter.export_leaderboard(sample_result, output_path)

        assert output_path.exists()
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["rank"] == "1"
        assert rows[0]["dut_id"] == "dut1"
        assert "elo" in rows[0]
        assert "wins" in rows[0]

    def test_export_comparisons(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting comparisons to CSV."""
        exporter = CSVExporter()
        output_path = tmp_path / "comparisons.csv"

        exporter.export_comparisons(sample_result, output_path)

        assert output_path.exists()
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["dut_a"] == "dut1"
        assert rows[0]["dut_b"] == "dut2"
        assert rows[0]["winner"] == "A"

    def test_export_comparisons_skipped_when_disabled(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test that comparisons export is skipped when disabled."""
        config = ExportConfig(include_comparisons=False)
        exporter = CSVExporter(config)
        output_path = tmp_path / "comparisons.csv"

        exporter.export_comparisons(sample_result, output_path)

        assert not output_path.exists()

    def test_export_errors(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting errors to CSV."""
        exporter = CSVExporter()
        output_path = tmp_path / "errors.csv"

        exporter.export_errors(sample_result, output_path)

        assert output_path.exists()
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["error_type"] == "APIError"
        assert rows[0]["dut_id"] == "dut1"
        assert "error_context" not in rows[0]  # Should be filtered out

    def test_export_errors_skipped_when_disabled(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test that errors export is skipped when disabled."""
        config = ExportConfig(include_errors=False)
        exporter = CSVExporter(config)
        output_path = tmp_path / "errors.csv"

        exporter.export_errors(sample_result, output_path)

        assert not output_path.exists()

    def test_export_errors_skipped_when_no_errors(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test that errors export is skipped when there are no errors."""
        sample_result.errors = []
        exporter = CSVExporter()
        output_path = tmp_path / "errors.csv"

        exporter.export_errors(sample_result, output_path)

        assert not output_path.exists()

    def test_decimal_places_config(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test that decimal places configuration is respected."""
        config = ExportConfig(decimal_places=2)
        exporter = CSVExporter(config)
        output_path = tmp_path / "leaderboard.csv"

        exporter.export_leaderboard(sample_result, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        # Check that cost is rounded to 2 decimal places
        assert row["total_cost_usd"] == "10.50"


class TestLaTeXExporter:
    """Tests for LaTeX exporter."""

    def test_export_leaderboard(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting leaderboard to LaTeX."""
        exporter = LaTeXExporter()
        output_path = tmp_path / "leaderboard.tex"

        exporter.export_leaderboard(sample_result, output_path)

        assert output_path.exists()
        content = output_path.read_text()

        assert "\\begin{table}" in content
        assert "\\end{table}" in content
        assert "dut1" in content
        assert "dut2" in content
        assert "1600" in content  # ELO rating

    def test_export_leaderboard_to_string(self, sample_result: TournamentResult) -> None:
        """Test exporting leaderboard to LaTeX string."""
        exporter = LaTeXExporter()
        latex_str = exporter.export_leaderboard_to_string(sample_result)

        assert "\\begin{table}" in latex_str
        assert "\\end{table}" in latex_str
        assert "dut1" in latex_str

    def test_export_summary_table(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting summary table to LaTeX."""
        exporter = LaTeXExporter()
        output_path = tmp_path / "summary.tex"

        exporter.export_summary_table(sample_result, output_path)

        assert output_path.exists()
        content = output_path.read_text()

        assert "\\begin{table}" in content
        assert "Tournament Summary Statistics" in content
        assert "Total Comparisons" in content
        assert "Errors" in content  # Should include errors section

    def test_latex_escaping(self, sample_result: TournamentResult) -> None:
        """Test that underscores in DUT IDs are escaped for LaTeX."""
        # Add a DUT with underscore in ID
        sample_result.ratings["test_dut"] = DUTRating(
            dut_id="test_dut",
            rating=BayesianELO(prior_mean=1400, prior_std=70),
            total_cost_usd=5.0,
            total_time_seconds=50.0,
            total_tokens=2000,
        )

        exporter = LaTeXExporter()
        latex_str = exporter.export_leaderboard_to_string(sample_result)

        # Should have escaped underscore
        assert "test\\_dut" in latex_str
        # Should not have unescaped underscore (outside of LaTeX commands)
        assert "test_dut" not in latex_str or "test\\_dut" in latex_str

    def test_decimal_places_config(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test that decimal places configuration is respected."""
        config = ExportConfig(decimal_places=2)
        exporter = LaTeXExporter(config)
        output_path = tmp_path / "summary.tex"

        exporter.export_summary_table(sample_result, output_path)

        content = output_path.read_text()

        # Check that cost is formatted with 2 decimal places
        assert "18.80" in content


class TestExportAllFormats:
    """Tests for export_all_formats convenience function."""

    def test_export_all_formats(self, sample_result: TournamentResult, tmp_path: Path) -> None:
        """Test exporting to all formats at once."""
        output_dir = tmp_path / "exports"

        exported = export_all_formats(sample_result, output_dir)

        assert "json" in exported
        assert "csv_leaderboard" in exported
        assert "csv_comparisons" in exported
        assert "csv_errors" in exported
        assert "latex_leaderboard" in exported
        assert "latex_summary" in exported

        # Verify all files exist
        assert exported["json"].exists()
        assert exported["csv_leaderboard"].exists()
        assert exported["csv_comparisons"].exists()
        assert exported["csv_errors"].exists()
        assert exported["latex_leaderboard"].exists()
        assert exported["latex_summary"].exists()

    def test_export_all_formats_without_comparisons(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test exporting all formats without comparisons."""
        config = ExportConfig(include_comparisons=False)
        output_dir = tmp_path / "exports"

        exported = export_all_formats(sample_result, output_dir, config)

        assert "csv_comparisons" not in exported
        assert "json" in exported

    def test_export_all_formats_without_errors(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test exporting all formats without errors."""
        config = ExportConfig(include_errors=False)
        output_dir = tmp_path / "exports"

        exported = export_all_formats(sample_result, output_dir, config)

        assert "csv_errors" not in exported
        assert "json" in exported

    def test_export_all_formats_creates_directory(
        self, sample_result: TournamentResult, tmp_path: Path
    ) -> None:
        """Test that export_all_formats creates output directory."""
        output_dir = tmp_path / "new_dir" / "exports"

        export_all_formats(sample_result, output_dir)

        assert output_dir.exists()
