#!/usr/bin/env python3
"""Validator for lf-7222: fix operator overloading with multiple interfaces.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_FILE = "integration_tests/operator_overloading_10.f90"
INJECTED_TEST = """\
module operator_overloading_10_module
   implicit none

   type :: first_type
      integer :: x
   end type

   type :: second_type
      integer :: x
   end type

   interface operator(/=)
      module procedure ne
   end interface

   interface operator(/=)
      module procedure une
   end interface

contains
   logical function ne(x, y)
      type(first_type), intent(in) :: x, y
      print *, "first_type::ne"
      ne = .false.
   end function

   logical function une(s, z)
      type(second_type), intent(in) :: s, z
      print *, "second_type::une"
      une = .false.
   end function
end module operator_overloading_10_module

program main
   use operator_overloading_10_module
   implicit none

   type(first_type) :: a1, a2
   type(second_type) :: b1, b2

   if (a1 /= a2) error stop
   if (b1 /= b2) error stop
end program main
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

    print("PASS: operator_overloading_10 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
