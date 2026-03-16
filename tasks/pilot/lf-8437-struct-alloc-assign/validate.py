#!/usr/bin/env python3
"""Validator for lf-8437: fix allocatable string component in derived type array.

The test file is injected from the fixed commit since it was added by the PR.
Acceptance: lfortran compiles and runs the test without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_FILE = "integration_tests/derived_types_79.f90"
INJECTED_TEST = """\
module m_labels_derived_types_79
    implicit none

    type :: toml_label
        character(:), allocatable :: source
    end type toml_label

    type :: toml_diagnostic
        type(toml_label), allocatable :: label(:)
    end type toml_diagnostic

end module m_labels_derived_types_79


module m_render_derived_types_79
    use m_labels_derived_types_79
    implicit none

contains

    function render_diagnostic(d) result(out)
        type(toml_diagnostic), intent(in) :: d
        character(:), allocatable :: out
        if (allocated(d%label)) then
            out = "Diagnostic: " // d%label(1)%source
        else
            out = "Empty diagnostic"
        end if
    end function render_diagnostic

end module m_render_derived_types_79


program derived_types_79
    use m_labels_derived_types_79
    use m_render_derived_types_79
    implicit none

    type(toml_diagnostic) :: diag
    type(toml_label) :: lbl(1)

    lbl(1)%source = "Something went wrong"
    diag%label = lbl

    print *, render_diagnostic(diag)
end program derived_types_79
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

    print("PASS: derived_types_79 compiled and ran successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
