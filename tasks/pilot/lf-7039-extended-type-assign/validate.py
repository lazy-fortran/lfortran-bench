#!/usr/bin/env python3
"""Validator for lf-7039: fix extended derived types assignment.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validator_support import materialize_fixed_test

TEST_FILE = "integration_tests/derived_types_49.f90"


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    test_path = workspace / TEST_FILE

    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

    test_path = materialize_fixed_test(
        workspace, TEST_FILE, Path(__file__).with_name("task.yaml")
    )

    result = subprocess.run(
        ["conda", "run", "-n", "lf-llvm11", str(lfortran), str(test_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        print(f"FAIL: lfortran exited with code {result.returncode}")
        if result.stderr:
            print(result.stderr[:500])
        return 1

    print("PASS: derived_types_49 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
