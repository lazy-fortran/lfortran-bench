#!/usr/bin/env python3
"""Validator for lf-6943: fix findloc for 2-D arrays.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_FILE = "integration_tests/intrinsics_374.f90"
INJECTED_TEST = """\
program intrinsics_370
    implicit none

    integer :: input(6, 9)
    character(len=2) :: str_arr(2, 2)
    integer, dimension(2) :: result

    input = reshape([&
        1,  2,  3,  4,  5,  7,  8,  9, 10, &
        11, 12, 13, 14, 7,  16, 17, 18, 19, &
        21, 22, 7,  24, 25, 26, 27, 28, 29, &
        31, 32, 33, 34, 35, 36, 37, 38, 39, &
        41, 42, 43, 44, 45, 46, 7,  48, 49, &
        51, 52, 53, 54, 55, 56, 57, 58, 7], [6, 9])

    str_arr = reshape(["aa", "bb", "cc", "aa"], [2, 2])

    result = findloc(input, 7)
    print *, result
    if (any(result /= [6, 1])) error stop

    result = findloc(input, 34)
    print *, result
    if (any(result /= [1, 6])) error stop

    result = findloc(input, 7, back=.true.)
    print *, result
    if (any(result /= [6, 9])) error stop

    result = findloc(str_arr, "cc")
    print *, result
    if (any(result /= [1, 2])) error stop

end program
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

    print("PASS: intrinsics_374 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
