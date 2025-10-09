"""Integration tests for CLI calibrate command."""

from pathlib import Path

from click.testing import CliRunner

from codegen_bench.cli.main import cli


def test_calibrate_command_with_sample_data():
    """Test calibrate command with sample ground truth data."""
    runner = CliRunner()

    # Use sample ground truth file from fixtures
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_file = fixtures_dir / "ground_truth_sample.yaml"

    result = runner.invoke(cli, ["calibrate", str(ground_truth_file), "--simulate"])

    # Command should succeed
    assert result.exit_code == 0

    # Check output contains expected elements
    assert "Calibrating judge:" in result.output
    assert "sample-calibration-set" in result.output
    assert "Calibration Results:" in result.output
    assert "Agreement Metrics:" in result.output
    assert "Bias Detection:" in result.output
    assert "Confusion Matrix:" in result.output
    assert "Recommendations:" in result.output


def test_calibrate_command_with_output_file(tmp_path):
    """Test calibrate command saves report to file."""
    runner = CliRunner()

    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_file = fixtures_dir / "ground_truth_sample.yaml"
    output_file = tmp_path / "calibration_report.txt"

    result = runner.invoke(
        cli, ["calibrate", str(ground_truth_file), "-o", str(output_file), "--simulate"]
    )

    # Command should succeed
    assert result.exit_code == 0

    # Output file should be created
    assert output_file.exists()

    # File should contain calibration report
    content = output_file.read_text()
    assert "Calibration Report:" in content
    assert "Agreement Metrics:" in content


def test_calibrate_command_with_verbose_report():
    """Test calibrate command with verbose output."""
    runner = CliRunner()

    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_file = fixtures_dir / "ground_truth_sample.yaml"

    result = runner.invoke(
        cli, ["calibrate", str(ground_truth_file), "--verbose-report", "--simulate"]
    )

    # Command should succeed
    assert result.exit_code == 0

    # Check verbose output includes detailed comparisons
    assert "Detailed Comparison Results:" in result.output
    assert "comp001" in result.output
    assert "comp002" in result.output


def test_calibrate_command_nonexistent_file():
    """Test calibrate command with non-existent ground truth file."""
    runner = CliRunner()

    result = runner.invoke(cli, ["calibrate", "/nonexistent/file.yaml", "--simulate"])

    # Command should fail
    assert result.exit_code != 0
    assert "Error: Ground truth file not found" in result.output


def test_calibrate_command_with_judge_option():
    """Test calibrate command with custom judge name."""
    runner = CliRunner()

    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_file = fixtures_dir / "ground_truth_sample.yaml"

    result = runner.invoke(
        cli, ["calibrate", str(ground_truth_file), "--judge", "test-judge", "--simulate"]
    )

    # Command should succeed
    assert result.exit_code == 0

    # Check judge name appears in output
    assert "Calibrating judge: test-judge" in result.output
    assert "Calibration Report: test-judge" in result.output


def test_calibrate_command_help():
    """Test calibrate command help text."""
    runner = CliRunner()

    result = runner.invoke(cli, ["calibrate", "--help"])

    # Command should succeed
    assert result.exit_code == 0

    # Check help text
    assert "Calibrate a judge against ground truth judgments" in result.output
    assert "--judge" in result.output
    assert "--output" in result.output
    assert "--verbose-report" in result.output
    assert "--simulate" in result.output


def test_calibrate_command_requires_simulate_flag():
    """Test calibrate command requires --simulate flag when judge not implemented."""
    runner = CliRunner()

    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    ground_truth_file = fixtures_dir / "ground_truth_sample.yaml"

    result = runner.invoke(cli, ["calibrate", str(ground_truth_file)])

    # Command should fail without --simulate
    assert result.exit_code != 0
    assert "Judge execution not yet implemented" in result.output
    assert "--simulate" in result.output
