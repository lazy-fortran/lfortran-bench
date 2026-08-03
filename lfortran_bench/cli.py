from __future__ import annotations

import argparse
from pathlib import Path

from lfortran_bench.core import check_task, run_suite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="lfortran-bench")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run-suite", help="Run a benchmark suite")
    run_parser.add_argument("suite", help="Path to suite YAML")
    run_parser.add_argument(
        "--output-dir",
        default="reports/latest",
        help="Directory for generated reports and per-run JSON",
    )
    run_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue after adapter or task failures",
    )

    check_parser = sub.add_parser("check-task", help="Verify a task oracle on base and fixed commits")
    check_parser.add_argument("task", help="Path to task YAML")
    check_parser.add_argument(
        "--output-dir",
        default="reports/task-check",
        help="Directory for oracle validation artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run-suite":
        return run_suite(Path(args.suite), Path(args.output_dir), args.continue_on_error)
    if args.command == "check-task":
        return check_task(Path(args.task), Path(args.output_dir))
    return 1
