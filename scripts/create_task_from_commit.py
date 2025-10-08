#!/usr/bin/env python3
"""Create a benchmark task YAML from a validated commit.

This script takes a commit that has been validated (tests pass before and after)
and creates a task YAML file suitable for the BrownBench benchmark suite.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_commit_info(repo_path: Path, sha: str) -> dict:
    """Get detailed commit information.

    Args:
        repo_path: Path to repository
        sha: Commit SHA

    Returns:
        Dict with commit details
    """
    # Get commit details
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "show",
            "--format=%an|%ae|%ad|%s|%b",
            "--date=short",
            "--stat",
            sha,
        ],
        capture_output=True,
        text=True,
    )

    lines = result.stdout.split("\n")
    header = lines[0].split("|")

    author = header[0]
    email = header[1]
    date = header[2]
    subject = header[3]
    body = header[4] if len(header) > 4 else ""

    # Get file changes
    files_changed = []
    for line in lines[1:]:
        if "|" in line and ("+" in line or "-" in line):
            filename = line.split("|")[0].strip()
            if filename:
                files_changed.append(filename)

    return {
        "sha": sha,
        "author": author,
        "email": email,
        "date": date,
        "subject": subject,
        "body": body,
        "files_changed": files_changed,
    }


def create_task_yaml(
    task_id: str,
    project_name: str,
    commit_info: dict,
    repo_path: Path,
    build_cmd: str | None,
    test_cmd: str | None,
    difficulty: str = "medium",
    domain: str = "refactoring",
) -> dict:
    """Create task YAML structure.

    Args:
        task_id: Unique task identifier
        project_name: Name of the project
        commit_info: Commit information from get_commit_info
        repo_path: Path to repository (for codebase_path)
        build_cmd: Build command
        test_cmd: Test command
        difficulty: Task difficulty (easy/medium/hard)
        domain: Task domain

    Returns:
        Task dictionary ready for YAML serialization
    """
    # Create specification from commit message
    specification = f"""Based on commit {commit_info['sha'][:10]} from {project_name}:

{commit_info['subject']}

{commit_info['body']}

Implement the changes described in this commit. The change should:
- Maintain the existing API/interface
- Pass all existing tests
- Follow the project's coding style

This is a real commit from the {project_name} repository, representing a typical
refactoring/enhancement task in a brownfield codebase.
""".strip()

    task = {
        "id": task_id,
        "name": commit_info["subject"][:80],  # Truncate long subjects
        "project": project_name,
        "domain": domain,
        "difficulty": difficulty,
        "codebase_path": f"submodules/{repo_path.name}",
        "specification": specification,
        "constraints": [
            "Must pass all existing tests",
            "Must maintain backward compatibility",
            "Must follow project coding conventions",
        ],
        "key_files": commit_info["files_changed"][:10],  # Limit to top 10 files
        "gotchas": [
            f"This is a real commit from {commit_info['date']}",
            "Review commit message carefully for context",
        ],
        "expected_human_time_minutes": estimate_time(len(commit_info["files_changed"])),
    }

    if build_cmd:
        task["compile_command"] = build_cmd

    if test_cmd:
        task["test_command"] = test_cmd

    return task


def estimate_time(num_files: int) -> int:
    """Estimate human time based on number of files changed.

    Args:
        num_files: Number of files changed

    Returns:
        Estimated minutes
    """
    if num_files <= 2:
        return 30
    elif num_files <= 5:
        return 60
    elif num_files <= 10:
        return 90
    else:
        return 120


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create benchmark task YAML from validated commit"
    )
    parser.add_argument("repo_path", type=Path, help="Path to git repository")
    parser.add_argument("commit_sha", help="Commit SHA to create task from")
    parser.add_argument("--task-id", required=True, help="Task ID (e.g., task_006)")
    parser.add_argument(
        "--project-name",
        required=True,
        help="Project name (e.g., git, redis, nginx)",
    )
    parser.add_argument("--build-cmd", help="Build command (optional)")
    parser.add_argument("--test-cmd", required=True, help="Test command (required)")
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Task difficulty",
    )
    parser.add_argument(
        "--domain",
        default="refactoring",
        help="Task domain (e.g., refactoring, bugfix, feature)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output YAML file (default: tasks/core/{task_id}.yaml)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.repo_path.exists():
        logger.error(f"Repository path does not exist: {args.repo_path}")
        sys.exit(1)

    # Get commit information
    logger.info(f"Gathering commit information for {args.commit_sha}...")
    commit_info = get_commit_info(args.repo_path, args.commit_sha)

    # Create task structure
    task = create_task_yaml(
        task_id=args.task_id,
        project_name=args.project_name,
        commit_info=commit_info,
        repo_path=args.repo_path,
        build_cmd=args.build_cmd,
        test_cmd=args.test_cmd,
        difficulty=args.difficulty,
        domain=args.domain,
    )

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = Path(f"tasks/core/{args.task_id}.yaml")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML
    logger.info(f"Writing task to {output_path}...")
    with open(output_path, "w") as f:
        yaml.dump(task, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    logger.info(f"✓ Task created successfully: {output_path}")
    print(f"\n✓ Task created successfully: {output_path}")
    print(f"\nTask details:")
    print(f"  ID: {task['id']}")
    print(f"  Name: {task['name']}")
    print(f"  Project: {task['project']}")
    print(f"  Difficulty: {task['difficulty']}")
    print(f"  Files changed: {len(task['key_files'])}")
    print(f"  Estimated time: {task['expected_human_time_minutes']} minutes")


if __name__ == "__main__":
    main()
