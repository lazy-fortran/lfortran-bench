#!/usr/bin/env python3
"""Validate bind(c) character interoperability using the upstream test pair."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validator_support import materialize_fixed_test

F90_FILE = "integration_tests/bindc_07.f90"
C_FILE = "integration_tests/bindc_07.c"


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

    f90_path = materialize_fixed_test(
        workspace, F90_FILE, Path(__file__).with_name("task.yaml")
    )
    c_path = materialize_fixed_test(
        workspace, C_FILE, Path(__file__).with_name("task.yaml")
    )
    result = subprocess.run(
        ["conda", "run", "-n", "lf-llvm11", str(lfortran), str(f90_path), str(c_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"FAIL: lfortran exited with code {result.returncode}")
        if result.stderr:
            print(result.stderr[:500])
        return 1
    print("PASS: bindc_07 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
