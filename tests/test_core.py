from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from lfortran_bench.adapters import AgentResponse
from lfortran_bench.core import check_task, run_suite


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def make_fixture_repo(root: Path) -> tuple[Path, str, str]:
    repo = root / "fixture-repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    (repo / "result.txt").write_text("broken\n")
    git(repo, "add", "result.txt")
    git(repo, "commit", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "result.txt").write_text("fixed\n")
    git(repo, "commit", "-am", "fix")
    fixed = git(repo, "rev-parse", "HEAD")
    return repo, base, fixed


def write_task(path: Path, repo: Path, base: str, fixed: str) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "id": "fixture-task",
                "title": "Fixture task",
                "repo_url": str(repo),
                "issue_url": "https://example.invalid/fixture",
                "issue_body": "Change result.txt from broken to fixed.",
                "base_commit": base,
                "fixed_commit": fixed,
                "acceptance_commands": [
                    "python -c \"from pathlib import Path; "
                    "assert Path('result.txt').read_text().strip() == 'fixed'\""
                ],
            }
        )
    )


class FixingAdapter:
    def stage(self, stage_index, prompt, workspace, run_dir, row, timeout_seconds):
        started = time.time()
        (workspace / "result.txt").write_text("fixed\n")
        return AgentResponse(
            ok=True,
            command=["fixture-adapter"],
            returncode=0,
            stdout="fixed",
            stderr="",
            duration_seconds=time.time() - started,
            text="fixed fixture",
        )


class CoreHarnessTests(unittest.TestCase):
    def test_check_task_verifies_base_fails_and_fixed_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, base, fixed = make_fixture_repo(root)
            task_path = root / "tasks" / "fixture" / "task.yaml"
            write_task(task_path, repo, base, fixed)
            output = root / "check-output"

            status = check_task(task_path, output)
            report = json.loads((output / "oracle.json").read_text())

        self.assertEqual(status, 0)
        self.assertTrue(report["ok"])
        self.assertFalse(report["base_acceptance"]["ok"])
        self.assertTrue(report["fixed_acceptance"]["ok"])

    def test_run_suite_uses_adapter_and_records_solution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, base, fixed = make_fixture_repo(root)
            task_path = root / "tasks" / "fixture" / "task.yaml"
            write_task(task_path, repo, base, fixed)
            suites = root / "suites"
            suites.mkdir()
            suite_path = suites / "fixture.yaml"
            suite_path.write_text(
                yaml.safe_dump(
                    {
                        "name": "fixture-suite",
                        "tasks": ["tasks/fixture/task.yaml"],
                        "rows": [
                            {
                                "name": "fixture-row",
                                "adapter": "fixture",
                                "run_judges": False,
                                "stage_budget_seconds": [5],
                            }
                        ],
                    }
                )
            )
            output = root / "suite-output"

            with patch("lfortran_bench.core.build_adapter", return_value=FixingAdapter()):
                status = run_suite(suite_path, output, continue_on_error=False)
            results = json.loads((output / "results.json").read_text())

        self.assertEqual(status, 0, results)
        self.assertEqual(results[0]["final_status"], "solved")
        self.assertEqual(results[0]["solved_stage"], 1)


if __name__ == "__main__":
    unittest.main()
