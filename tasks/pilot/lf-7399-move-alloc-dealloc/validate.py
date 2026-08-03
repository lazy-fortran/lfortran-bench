#!/usr/bin/env python3
"""Validate move_alloc source deallocation with a strengthened upstream test."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validator_support import materialize_fixed_test

TEST_FILE = "integration_tests/intrinsics_378.f90"


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

    test_path = materialize_fixed_test(
        workspace, TEST_FILE, Path(__file__).with_name("task.yaml")
    )
    source = test_path.read_text()
    marker = "  print *, allocated(a)\n\nend program intrinsics_378"
    if marker not in source:
        print("FAIL: upstream intrinsics_378 test format changed")
        return 1
    test_path.write_text(
        source.replace(
            marker,
            "  print *, allocated(a)\n  if (allocated(a)) error stop\n\nend program intrinsics_378",
            1,
        )
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
    print("PASS: intrinsics_378 compiled and passed the source deallocation assertion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
