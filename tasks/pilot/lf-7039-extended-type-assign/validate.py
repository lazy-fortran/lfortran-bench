#!/usr/bin/env python3
"""Validator for lf-7039: fix extended derived types assignment.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_FILE = "integration_tests/derived_types_49.f90"
INJECTED_TEST = """\
module derived_types_49_m
    implicit none
    public :: base, derived

    type, abstract :: base
        integer :: a
    end type base

    type, extends(base) :: derived
        integer :: b
    end type derived

    type, extends(derived) :: derived2
        integer :: c
        integer :: d
    end type derived2
end module derived_types_49_m

program derived_types_49
  use derived_types_49_m
  implicit none

  type(derived2) :: set0, set1
  set0 = derived2(10, 20, 30, 40)

  set1 = set0

  if (set1%a /= set0%a) error stop
  if (set1%b /= set0%b) error stop
  if (set1%c /= set0%c) error stop
  if (set1%d /= set0%d) error stop
end program derived_types_49
"""


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    test_path = workspace / TEST_FILE

    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

    # Always inject: overwrite any stale or mismatched file from the workspace
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(INJECTED_TEST)

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
