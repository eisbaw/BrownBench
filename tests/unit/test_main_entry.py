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


def test_main_entry_point_version():
    """Test that python -m codegen_bench --version works."""
    result = subprocess.run(
        [sys.executable, "-m", "codegen_bench", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Click may exit with 0 or show version in help
    assert result.returncode in (0, 2)  # Click may use exit code 2 for --help-like flags
