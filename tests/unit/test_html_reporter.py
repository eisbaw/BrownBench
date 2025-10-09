"""Unit tests for HTML reporter."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from codegen_bench.core.judgment import JudgmentResult
from codegen_bench.core.tournament import DUTRating, TournamentResult
from codegen_bench.reporting.html import HTMLReporter
from codegen_bench.stats.ratings.bayesian_elo import BayesianELO


@pytest.fixture
def sample_tournament_result() -> TournamentResult:
    """Create a sample tournament result for testing."""
    # Create ratings for 3 DUTs
    ratings = {}

    dut1_rating = BayesianELO()
    dut1_rating.mean = 1500.0
    dut1_rating.std = 50.0
    ratings["dut1"] = DUTRating(
        dut_id="dut1",
        rating=dut1_rating,
        total_cost_usd=0.15,
        total_time_seconds=45.5,
        total_tokens=1200,
    )

    dut2_rating = BayesianELO()
    dut2_rating.mean = 1450.0
    dut2_rating.std = 60.0
    ratings["dut2"] = DUTRating(
        dut_id="dut2",
        rating=dut2_rating,
        total_cost_usd=0.12,
        total_time_seconds=38.2,
        total_tokens=950,
    )

    dut3_rating = BayesianELO()
    dut3_rating.mean = 1400.0
    dut3_rating.std = 55.0
    ratings["dut3"] = DUTRating(
        dut_id="dut3",
        rating=dut3_rating,
        total_cost_usd=0.10,
        total_time_seconds=35.0,
        total_tokens=800,
    )

    # Create sample comparisons
    comparisons = [
        (
            "dut1",
            "dut2",
            "correctness",
            JudgmentResult(winner="A", votes=["A"], agreement_rate=1.0, confidence=0.95),
        ),
        (
            "dut1",
            "dut3",
            "correctness",
            JudgmentResult(winner="A", votes=["A"], agreement_rate=1.0, confidence=0.90),
        ),
        (
            "dut2",
            "dut3",
            "correctness",
            JudgmentResult(winner="A", votes=["A"], agreement_rate=1.0, confidence=0.85),
        ),
        (
            "dut1",
            "dut2",
            "maintainability",
            JudgmentResult(winner="TIE", votes=["TIE"], agreement_rate=1.0, confidence=0.80),
        ),
    ]

    # Add comparisons to DUT histories
    for comp in comparisons:
        dut_a, dut_b = comp[0], comp[1]
        if dut_a in ratings:
            ratings[dut_a]._comparisons.append(comp)
        if dut_b in ratings:
            ratings[dut_b]._comparisons.append(comp)

    return TournamentResult(
        ratings=ratings,
        comparisons=comparisons,
        tasks_evaluated=["task1", "task2"],
        arenas=["correctness", "maintainability"],
        total_comparisons=4,
        total_cost_usd=0.37,
        start_time=1000.0,
        end_time=1100.0,
        errors=[],
    )


class TestHTMLReporter:
    """Tests for HTML reporter."""

    def test_init(self) -> None:
        """Test reporter initialization."""
        reporter = HTMLReporter()
        assert reporter.env is not None
        assert "format_float" in reporter.env.filters
        assert "format_cost" in reporter.env.filters
        assert "format_time" in reporter.env.filters

    def test_format_float(self) -> None:
        """Test float formatting."""
        reporter = HTMLReporter()
        assert reporter._format_float(3.14159, 2) == "3.14"
        assert reporter._format_float(3.14159, 3) == "3.142"
        assert reporter._format_float(100.0, 1) == "100.0"

    def test_format_cost(self) -> None:
        """Test cost formatting."""
        reporter = HTMLReporter()
        assert reporter._format_cost(0.1234) == "$0.1234"
        assert reporter._format_cost(1.5) == "$1.5000"
        assert reporter._format_cost(0.0001) == "$0.0001"

    def test_format_time(self) -> None:
        """Test time formatting."""
        reporter = HTMLReporter()
        assert reporter._format_time(30.0) == "30.0s"
        assert reporter._format_time(90.0) == "1.5min"
        assert reporter._format_time(3600.0) == "1.00h"
        assert reporter._format_time(7200.0) == "2.00h"

    def test_generate_report_creates_file(self, sample_tournament_result: TournamentResult) -> None:
        """Test that generate_report creates an HTML file."""
        reporter = HTMLReporter()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            reporter.generate_report(
                sample_tournament_result,
                output_path,
                title="Test Tournament",
                include_pareto=False,
            )

            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_generate_report_contains_expected_content(
        self, sample_tournament_result: TournamentResult
    ) -> None:
        """Test that generated HTML contains expected content."""
        reporter = HTMLReporter()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            reporter.generate_report(
                sample_tournament_result,
                output_path,
                title="Test Tournament",
                include_pareto=False,
            )

            content = output_path.read_text()

            # Check title
            assert "Test Tournament" in content

            # Check metadata
            assert "4" in content  # total comparisons

            # Check DUT IDs in leaderboard
            assert "dut1" in content
            assert "dut2" in content
            assert "dut3" in content

            # Check arenas
            assert "correctness" in content
            assert "maintainability" in content

            # Check tasks
            assert "task1" in content
            assert "task2" in content

    def test_generate_report_with_pareto(self, sample_tournament_result: TournamentResult) -> None:
        """Test report generation with Pareto frontier."""
        reporter = HTMLReporter()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            reporter.generate_report(
                sample_tournament_result,
                output_path,
                title="Test with Pareto",
                include_pareto=True,
            )

            content = output_path.read_text()
            assert "Pareto Frontier" in content

    def test_create_elo_chart(self, sample_tournament_result: TournamentResult) -> None:
        """Test ELO chart creation."""
        reporter = HTMLReporter()
        chart_html = reporter._create_elo_chart(sample_tournament_result)

        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "plotly" in chart_html.lower()
        assert "dut1" in chart_html
        assert "dut2" in chart_html
        assert "dut3" in chart_html

    def test_create_cost_chart(self, sample_tournament_result: TournamentResult) -> None:
        """Test cost chart creation."""
        reporter = HTMLReporter()
        chart_html = reporter._create_cost_chart(sample_tournament_result)

        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "plotly" in chart_html.lower()

    def test_create_wlt_chart(self, sample_tournament_result: TournamentResult) -> None:
        """Test win/loss/tie chart creation."""
        reporter = HTMLReporter()
        chart_html = reporter._create_wlt_chart(sample_tournament_result)

        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "plotly" in chart_html.lower()
        assert "Wins" in chart_html
        assert "Losses" in chart_html
        assert "Ties" in chart_html

    def test_create_arena_performance_chart(
        self, sample_tournament_result: TournamentResult
    ) -> None:
        """Test arena performance heatmap creation."""
        reporter = HTMLReporter()
        chart_html = reporter._create_arena_performance_chart(sample_tournament_result)

        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "plotly" in chart_html.lower()
        assert "correctness" in chart_html
        assert "maintainability" in chart_html

    def test_create_pareto_chart(self, sample_tournament_result: TournamentResult) -> None:
        """Test Pareto chart creation."""
        reporter = HTMLReporter()
        chart_html = reporter._create_pareto_chart(sample_tournament_result)

        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "plotly" in chart_html.lower()
        assert "Pareto" in chart_html

    def test_compute_arena_breakdowns(self, sample_tournament_result: TournamentResult) -> None:
        """Test arena breakdown computation."""
        reporter = HTMLReporter()
        breakdowns = reporter._compute_arena_breakdowns(sample_tournament_result)

        assert len(breakdowns) == 2  # correctness and maintainability
        assert all("name" in b for b in breakdowns)
        assert all("total_comparisons" in b for b in breakdowns)
        assert all("avg_agreement" in b for b in breakdowns)
        assert all("tie_count" in b for b in breakdowns)
        assert all("tie_rate" in b for b in breakdowns)

        # Find correctness arena
        correctness_breakdown = next(b for b in breakdowns if b["name"] == "correctness")
        assert correctness_breakdown["total_comparisons"] == 3

        # Find maintainability arena
        maintainability_breakdown = next(b for b in breakdowns if b["name"] == "maintainability")
        assert maintainability_breakdown["total_comparisons"] == 1
        assert maintainability_breakdown["tie_count"] == 1

    def test_compute_error_summary_no_errors(
        self, sample_tournament_result: TournamentResult
    ) -> None:
        """Test error summary with no errors."""
        reporter = HTMLReporter()
        summary = reporter._compute_error_summary(sample_tournament_result)

        assert summary["total"] == 0
        assert summary["by_phase"] == {}
        assert summary["by_type"] == {}

    def test_html_is_valid_structure(self, sample_tournament_result: TournamentResult) -> None:
        """Test that generated HTML has valid structure."""
        reporter = HTMLReporter()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            reporter.generate_report(
                sample_tournament_result,
                output_path,
                title="Structure Test",
                include_pareto=False,
            )

            content = output_path.read_text()

            # Check basic HTML structure
            assert "<!DOCTYPE html>" in content
            assert "<html" in content
            assert "</html>" in content
            assert "<head>" in content
            assert "</head>" in content
            assert "<body>" in content
            assert "</body>" in content
            assert "<title>" in content
            assert "</title>" in content

    def test_report_with_custom_title(self, sample_tournament_result: TournamentResult) -> None:
        """Test report with custom title."""
        reporter = HTMLReporter()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            custom_title = "Custom Test Title"
            reporter.generate_report(
                sample_tournament_result,
                output_path,
                title=custom_title,
                include_pareto=False,
            )

            content = output_path.read_text()
            assert custom_title in content

    def test_charts_dictionary_structure(self, sample_tournament_result: TournamentResult) -> None:
        """Test that _create_charts returns expected dictionary structure."""
        reporter = HTMLReporter()

        # Without Pareto
        charts = reporter._create_charts(sample_tournament_result, include_pareto=False)
        assert "elo_ratings" in charts
        assert "cost_analysis" in charts
        assert "wlt_chart" in charts
        assert "arena_performance" in charts
        assert "pareto_frontier" not in charts

        # With Pareto
        charts_with_pareto = reporter._create_charts(sample_tournament_result, include_pareto=True)
        assert "pareto_frontier" in charts_with_pareto
