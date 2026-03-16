#!/usr/bin/env python3
"""Validator for lf-7399: fix deallocate variable in move_alloc after assignment.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

<<<<<<< HEAD:tasks/pilot/lf-8373-select-type-associate/validate.py
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validator_support import materialize_fixed_test

TEST_FILE = "integration_tests/select_type_11.f90"
=======
TEST_FILE = "integration_tests/intrinsics_378.f90"
INJECTED_TEST = """\
program intrinsics_378
  implicit none
  integer, allocatable :: a(:), b(:)

  allocate(a(3), b(3))
  a = [1, 2, 3]

  call move_alloc(a, b)

  print *, allocated(a)

end program intrinsics_378
"""
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks):tasks/pilot/lf-7399-move-alloc-dealloc/validate.py


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    test_path = workspace / TEST_FILE

    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

<<<<<<< HEAD:tasks/pilot/lf-8373-select-type-associate/validate.py
    test_path = materialize_fixed_test(
        workspace, TEST_FILE, Path(__file__).with_name("task.yaml")
    )
=======
    # Always inject: overwrite any stale or mismatched file from the workspace
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(INJECTED_TEST)
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks):tasks/pilot/lf-7399-move-alloc-dealloc/validate.py

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

    print("PASS: intrinsics_378 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
