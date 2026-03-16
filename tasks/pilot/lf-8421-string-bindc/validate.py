#!/usr/bin/env python3
"""Validator for lf-8421: fix bind(c) character array interoperability.

The test requires both a Fortran file and a C file, injected from the fixed
commit since they were added by the PR.  The C file provides the bind(c)
functions that the Fortran program calls.
Acceptance: lfortran compiles both files together and runs without errors.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

<<<<<<< HEAD
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validator_support import materialize_fixed_test

TEST_FILE = "integration_tests/bindc_07.f90"
=======
F90_FILE = "integration_tests/bindc_07.f90"
C_FILE = "integration_tests/bindc_07.c"

INJECTED_F90 = """\
program bindc_07
  use iso_c_binding, only: c_char, c_ptr, c_null_ptr, c_size_t, c_int, c_associated, c_f_pointer
  implicit none

  interface
     function test_getcwd(buf, size) result(res) bind(c, name="getcwd_dummy")
       import c_char, c_size_t, c_ptr
       character(kind=c_char,len=1), intent(out) :: buf
       integer(c_size_t), value, intent(in) :: size
       type(c_ptr) :: res
     end function test_getcwd

     function test_char_array(buf, len) result(res) bind(c, name="test_char_array")
      import c_char, c_int, c_ptr
      character(kind=c_char), dimension(*), intent(inout) :: buf
      integer(c_int), value, intent(in) :: len
      type(c_ptr) :: res
   end function test_char_array
  end interface

  ! Test variables
  character(len=1024) :: large_result
  character(len=1) :: small_result(256)
  character(len=50) :: medium_result
  type(c_ptr) :: ptr_result
  integer :: i
  type(c_ptr) :: res_ptr

  print *, "=== ROBUST BIND(C) CHARACTER ARRAY TEST ==="
  print *, ""

  ! Test 1: Large character variable
  print *, "TEST 1: Large character variable"
  large_result = repeat(' ', len(large_result))
  ptr_result = test_getcwd(large_result, int(len(large_result), c_size_t))

  if (c_associated(ptr_result)) then
     print *, "SUCCESS: Large buffer test passed"
     print *, "Result: '", trim(large_result), "'"
  else
     print *, "FAILED: Large buffer test failed"
  end if
  print *, ""

  ! Test 2: Array of single characters

  print *, "TEST 2: Array of single characters"
  small_result = ' '
  res_ptr = test_char_array(small_result, int(size(small_result), c_int))

  if (c_associated(res_ptr)) then
    print *, "SUCCESS: Small array test passed"
    write(*,'(A)', advance='no') "Result: '"
    do i = 1, min(size(small_result), 50)
        if (small_result(i) == char(0)) exit
        write(*,'(A)', advance='no') ,small_result(i)
    end do
    write(*,'(A)') "'"
  else
    print *, "FAILED: Small array test failed"
  end if


  ! Test 3: Medium character variable
  print *, "TEST 3: Medium character variable"
  medium_result = repeat(' ', len(medium_result))
  ptr_result = test_getcwd(medium_result, int(len(medium_result), c_size_t))

  if (c_associated(ptr_result)) then
     print *, "SUCCESS: Medium buffer test passed"
     print *, "Result: '", trim(medium_result), "'"
  else
     print *, "FAILED: Medium buffer test failed"
  end if

  print *, ""
  print *, "=== ALL TESTS COMPLETED ==="

end program bindc_07
"""
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks)

INJECTED_C = """\
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
// Dummy getcwd function that mimics the real getcwd behavior
char* getcwd_dummy(char* buf, size_t size) {
    const char* dummy_path = "/home/user/test/directory";
    size_t path_len = strlen(dummy_path);

    if (buf == NULL) {
        printf("ERROR: Received NULL buffer pointer!\\n");
        return NULL;
    }

    if (size <= path_len) {
        printf("ERROR: Buffer too small! Need %zu, got %zu\\n", path_len + 1, size);
        return NULL;
    }

    // Debug: Print what we received
    printf("C function received:\\n");
    printf("  - Buffer pointer: %p\\n", (void*)buf);
    printf("  - Buffer size: %zu\\n", size);

    // Copy the dummy path to the buffer
    strcpy(buf, dummy_path);

    printf("  - Copied path: '%s'\\n", buf);
    printf("  - Path length: %zu\\n", strlen(buf));

    return buf;  // Return the buffer pointer on success
}

char* test_char_array(char* buffer, int len) {
    printf("C test_char_array received:\\n");
    printf("  - Buffer pointer: %p\\n", (void*)buffer);
    printf("  - Length parameter: %d\\n", len);

    if (buffer == NULL) {
        printf("  - ERROR: NULL buffer!\\n");
        return NULL;
    }

    // Write a test string
    const char* test_str = "Hello from C!";
    strncpy(buffer, test_str, len - 1);
    buffer[len - 1] = '\\0';
    printf("  - Wrote to buffer: '%s'\\n", buffer);
    return buffer;
}
"""


def main() -> int:
    workspace = Path(sys.argv[1])
    lfortran = workspace / "build" / "src" / "bin" / "lfortran"
    f90_path = workspace / F90_FILE
    c_path = workspace / C_FILE

    if not lfortran.exists():
        print(f"FAIL: lfortran binary not found at {lfortran}")
        return 1

<<<<<<< HEAD
    test_path = materialize_fixed_test(
        workspace, TEST_FILE, Path(__file__).with_name("task.yaml")
    )
=======
    # Always inject both files to ensure correctness
    f90_path.parent.mkdir(parents=True, exist_ok=True)
    f90_path.write_text(INJECTED_F90)
    c_path.write_text(INJECTED_C)
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks)

    # Compile and run with both the Fortran and C files
    result = subprocess.run(
        [
            "conda", "run", "-n", "lf-llvm11",
            str(lfortran), str(f90_path), str(c_path),
        ],
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
