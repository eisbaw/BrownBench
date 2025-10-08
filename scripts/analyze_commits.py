#!/usr/bin/env python3
"""Analyze git repository commit history to find suitable benchmark tasks.

Criteria for suitable commits:
- 50-500 lines of code changed
- Ideally has passing tests before and after
- Self-contained (not part of a large feature)
- Changes production code (not just tests or docs)
"""

import argparse
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for commit filtering
MIN_CHANGES = 50
MAX_CHANGES = 500
IDEAL_CHANGES = 200


@dataclass
class CommitCandidate:
    """A candidate commit for creating a benchmark task."""

    sha: str
    author: str
    date: str
    subject: str
    lines_added: int
    lines_deleted: int
    files_changed: int
    total_changes: int

    @property
    def size_category(self) -> str:
        """Categorize commit by size."""
        if self.total_changes < MIN_CHANGES:
            return "too_small"
        elif self.total_changes <= 150:
            return "small"
        elif self.total_changes <= 300:
            return "medium"
        elif self.total_changes <= MAX_CHANGES:
            return "large"
        else:
            return "too_large"


def run_git_command(repo_path: Path, *args: str) -> str:
    """Run a git command in the repository."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_commit_stats(repo_path: Path, sha: str) -> tuple[int, int, int]:
    """Get statistics for a commit.

    Returns:
        (lines_added, lines_deleted, files_changed)
    """
    stats_output = run_git_command(repo_path, "show", "--shortstat", "--format=", sha)

    if not stats_output:
        return (0, 0, 0)

    # Parse output like: " 2 files changed, 45 insertions(+), 12 deletions(-)"
    parts = stats_output.split(",")

    files_changed = 0
    lines_added = 0
    lines_deleted = 0

    for part in parts:
        part = part.strip()
        if "file" in part:
            files_changed = int(part.split()[0])
        elif "insertion" in part:
            lines_added = int(part.split()[0])
        elif "deletion" in part:
            lines_deleted = int(part.split()[0])

    return (lines_added, lines_deleted, files_changed)


def is_suitable_commit(repo_path: Path, sha: str) -> bool:
    """Check if commit modifies production code (not just tests/docs)."""
    # Get list of changed files
    files = run_git_command(repo_path, "show", "--name-only", "--format=", sha).split("\n")

    # Filter out test and doc files
    code_files = [
        f
        for f in files
        if f
        and not any(
            pattern in f.lower()
            for pattern in [
                "test",
                "spec",
                "doc",
                "readme",
                "changelog",
                "license",
                ".md",
                ".txt",
                ".rst",
            ]
        )
    ]

    # Must have at least one production code file
    return len(code_files) > 0


def analyze_repository(repo_path: Path, limit: int = 1000) -> list[CommitCandidate]:
    """Analyze repository commit history.

    Args:
        repo_path: Path to git repository
        limit: Maximum number of commits to analyze

    Returns:
        List of suitable commit candidates
    """
    logger.info(f"Analyzing {repo_path.name}...")

    # Get recent commit list
    commit_list = run_git_command(
        repo_path,
        "log",
        f"--max-count={limit}",
        "--format=%H|%an|%ad|%s",
        "--date=short",
    ).split("\n")

    candidates = []
    skipped_count = 0

    for line in commit_list:
        if not line:
            continue

        sha, author, date, subject = line.split("|", 3)

        # Get commit statistics
        try:
            lines_added, lines_deleted, files_changed = get_commit_stats(repo_path, sha)
            total_changes = lines_added + lines_deleted

            # Filter by size
            if total_changes < MIN_CHANGES or total_changes > MAX_CHANGES:
                logger.debug(f"Skipping {sha[:10]}: {total_changes} changes (out of range)")
                skipped_count += 1
                continue

            # Check if it's a suitable commit (modifies production code)
            if not is_suitable_commit(repo_path, sha):
                logger.debug(f"Skipping {sha[:10]}: no production code changes")
                skipped_count += 1
                continue

            candidate = CommitCandidate(
                sha=sha,
                author=author,
                date=date,
                subject=subject,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                files_changed=files_changed,
                total_changes=total_changes,
            )

            candidates.append(candidate)

        except subprocess.CalledProcessError as e:
            logger.warning(f"Error processing commit {sha[:10]}: {e}")
            skipped_count += 1
            continue

    logger.info(f"Found {len(candidates)} candidates, skipped {skipped_count} commits")
    return candidates


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze git repository for benchmark tasks")
    parser.add_argument("repo_path", type=Path, help="Path to git repository")
    parser.add_argument("--limit", type=int, default=1000, help="Max commits to analyze")
    parser.add_argument("--max-candidates", type=int, default=30, help="Max candidates to return")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.repo_path.exists():
        logger.error(f"Repository path does not exist: {args.repo_path}")
        sys.exit(1)

    # Analyze repository
    candidates = analyze_repository(args.repo_path, args.limit)

    # Sort by total changes (prefer medium-sized commits near IDEAL_CHANGES)
    candidates.sort(key=lambda c: abs(c.total_changes - IDEAL_CHANGES))

    # Take top candidates
    candidates = candidates[: args.max_candidates]

    # Print results
    logger.info(f"\nFound {len(candidates)} suitable candidates:\n")
    print(f"\nFound {len(candidates)} suitable candidates:\n")
    print(f"{'SHA':<12} {'Date':<12} {'Changes':<10} {'Files':<8} {'Subject':<60}")
    print("-" * 110)

    for c in candidates:
        subject = c.subject[:57] + "..." if len(c.subject) > 60 else c.subject
        print(
            f"{c.sha[:10]:<12} {c.date:<12} "
            f"{c.total_changes:<10} {c.files_changed:<8} {subject:<60}"
        )

    # Write detailed output to file
    output_file = Path(f"{args.repo_path.name}_candidates.txt")
    with open(output_file, "w") as f:
        f.write(f"Commit candidates for {args.repo_path.name}\n")
        f.write("=" * 80 + "\n\n")

        for c in candidates:
            f.write(f"SHA: {c.sha}\n")
            f.write(f"Author: {c.author}\n")
            f.write(f"Date: {c.date}\n")
            f.write(f"Subject: {c.subject}\n")
            f.write(
                f"Changes: +{c.lines_added}/-{c.lines_deleted} "
                f"(total: {c.total_changes}, files: {c.files_changed})\n"
            )
            f.write(f"Size: {c.size_category}\n")
            f.write("-" * 80 + "\n\n")

    print(f"\nDetailed output written to: {output_file}")


if __name__ == "__main__":
    main()
