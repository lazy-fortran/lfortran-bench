#!/usr/bin/env python3
"""Validator for lf-8312: fix common block variable access from contained subroutine.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_FILE = "integration_tests/common_14.f90"
INJECTED_TEST = """\
program common_14
    implicit none
    real :: x, y

    common /coords/ x, y

    x = 5.0
    y = 10.0

    call show_coords
contains
    subroutine show_coords
        implicit none
        real :: x, y
        common /coords/ x, y
        print *, "x =", x, ", y =", y
        if ( abs(x - 5.0) > 1e-8 ) error stop
        if ( abs(y - 10.0) > 1e-8 ) error stop
    end subroutine show_coords
end program common_14
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

    print("PASS: common_14 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
