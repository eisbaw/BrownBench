"""Task loader with validation."""

from pathlib import Path

import yaml

from codegen_bench.core.task import Task
from codegen_bench.exceptions import TaskError, ValidationError


class TaskLoader:
    """Load tasks from various sources."""

    def __init__(self, base_path: Path):
        """Initialize task loader.

        Args:
            base_path: Base directory containing task definitions
        """
        self.base_path = base_path

    def load_task(self, task_id: str) -> Task:
        """Load single task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task object

        Raises:
            FileNotFoundError: If task file doesn't exist
            ValueError: If task validation fails
        """
        # Try direct path first
        path = self.base_path / f"{task_id}.yaml"
        if not path.exists():
            # Try looking in subdirectories
            matches = list(self.base_path.rglob(f"{task_id}.yaml"))
            if not matches:
                raise FileNotFoundError(f"Task {task_id} not found in {self.base_path}")
            path = matches[0]

        task = Task.from_yaml(path)

        # Validate task (raises ValidationError with details if invalid)
        try:
            task.validate()
        except ValidationError as e:
            # Wrap ValidationError as TaskError to maintain interface
            raise TaskError(str(e)) from e

        return task

    def load_task_set(self, name: str) -> list[Task]:
        """Load predefined task set.

        Args:
            name: Task set name (core, embedded, all) or glob pattern

        Returns:
            List of Task objects

        Raises:
            ValueError: If any task fails validation
        """
        if name == "core":
            pattern = "core/*.yaml"
        elif name == "embedded":
            pattern = "embedded/*.yaml"
        elif name == "all":
            pattern = "**/*.yaml"
        else:
            # Custom pattern
            pattern = name

        paths = sorted(self.base_path.glob(pattern))
        if not paths:
            raise FileNotFoundError(f"No tasks found matching pattern: {pattern}")

        tasks = []
        for path in paths:
            try:
                task = Task.from_yaml(path)
                task.validate()  # Raises ValidationError with details if invalid
                tasks.append(task)
            except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, ValidationError) as e:
                # OSError: file read errors (includes IOError in Python 3.3+)
                # ValueError: validation errors (now from shlex.split)
                # KeyError: missing required fields in dict
                # TypeError: missing required __init__ arguments
                # yaml.YAMLError: YAML parsing errors (includes ParserError)
                # ValidationError: task validation failures
                raise TaskError(f"Failed to load task from {path}: {e}") from e

        return tasks

    def list_available_tasks(self) -> list[str]:
        """List all available task IDs.

        Returns:
            List of task IDs
        """
        tasks = []
        for path in self.base_path.rglob("*.yaml"):
            try:
                task = Task.from_yaml(path)
                tasks.append(task.id)
            except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, ValidationError):
                # Skip invalid tasks
                # OSError: file read errors (includes IOError in Python 3.3+)
                # ValueError: validation errors (now from shlex.split)
                # KeyError: missing required fields in dict
                # TypeError: missing required __init__ arguments
                # yaml.YAMLError: YAML parsing errors (includes ParserError)
                # ValidationError: task validation failures
                continue
        return sorted(tasks)
