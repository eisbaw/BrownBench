"""Tests for __main__.py entry point."""

import subprocess
import sys


def test_main_entry_point_help():
    """Test that python -m codegen_bench works."""
    result = subprocess.run(
        [sys.executable, "-m", "codegen_bench", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0
    assert "AI Code Generation Benchmark" in result.stdout


def test_main_entry_point_invalid_option():
    """Test that python -m codegen_bench with invalid option fails gracefully."""
    result = subprocess.run(
        [sys.executable, "-m", "codegen_bench", "--nonexistent"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Click exits with 2 for invalid options
    assert result.returncode == 2
    assert "No such option" in result.stdout or "No such option" in result.stderr
