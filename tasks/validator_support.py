from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def materialize_fixed_test(workspace: Path, test_file: str, task_yaml: Path) -> Path:
    """Copy the task's real regression test from its pinned fixed commit."""
    task = yaml.safe_load(task_yaml.read_text())
    result = subprocess.run(
        ["git", "show", f"{task['fixed_commit']}:{test_file}"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    destination = workspace / test_file
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.stdout)
    return destination
