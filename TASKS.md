# LFortran Bench Task Candidates

20 tasks from merged PRs before September 2025. All fix compiler bugs
in C++ code with integration test cases.

## Validation status

- [x] All 20 PRs verified to have integration tests
- [ ] Base commit build tested
- [ ] Fixed commit build tested
- [ ] Test fails at base, passes at fixed (oracle check)

## Selected Tasks

### Semantics / Type System
| # | PR | Files | Test file | Pattern | Title |
|---|---|---|---|---|---|
| 1 | #8504 | 7 | complex_implicit_cast.f90 | inject | Fix implicit cast for complex numbers |
| 2 | #8373 | 3 | select_type_11.f90 | inject | Handle Associate for class(*) vars |
| 3 | #7100 | 3 | derived_types_53.f90 | inject | ClassType to ClassType polymorphic arg conversion |
| 4 | #8200 | 2 | derived_types_72.f90 | exists | Get correct struct symbol from implied do loop |
| 5 | #8409 | 3 | select_type_12.f90 | inject | Handle StructInstanceMember association in select type |

### Array Operations
| # | PR | Files | Test file | Pattern | Title |
|---|---|---|---|---|---|
| 6 | #8490 | 3 | submodule_13.f90 | inject | Fix calling elemental function on array of derived types |
| 7 | #8481 | 4 | complex_array_member_access.f90 | inject | Fix complex array member access (%re and %im) |
| 8 | #8431 | 4 | arrays_reshape_29.f90 | inject | Handle some cases of array reshape |
| 9 | #8405 | 4 | arrays_reshape_25.f90 | inject | Handle using reshape with casting |
| 10 | #8401 | 2 | arrays_constructor_01.f90 | exists | Fix verify condition for compile-time constant arrays |

### String / I/O
| # | PR | Files | Test file | Pattern | Title |
|---|---|---|---|---|---|
| 11 | #8421 | 5 | bindc_07.f90 | inject | Handle string array passed to BindC function call |
| 12 | #8412 | 3 | nullify_07.f90 | inject | Handle string pointer in nullify() |
| 13 | #8352 | 5 | string_69.f90 | inject | Create allocatable temporary if string len is runtime |
| 14 | #8511 | 4 | read_05.f90 | inject | Accept READ with format literal and no unit |

### Code Generation
| # | PR | Files | Test file | Pattern | Title |
|---|---|---|---|---|---|
| 15 | #8390 | 4 | nested_16.f90 | exists | Handle nested structconstructor in declaring global vars |
| 16 | #8345 | 9 | implied_do_loops11.f90 | inject | Compile-time evaluation of implied-do loops for parameter arrays |
| 17 | #7900 | 3 | arrays_13_size.f90 | inject | Correct ExternalSymbol condition for FunctionCall in IntegerBinOp |

### Struct / Derived Types
| # | PR | Files | Test file | Pattern | Title |
|---|---|---|---|---|---|
| 18 | #8150 | 3 | intrinsics_392.f90 | inject | Handle optional args in nested subroutines |
| 19 | #8041 | 3 | intrinsics_391.f90 | inject | Fix compile-time eval of parameter expressions with intrinsics |
| 20 | #5987 | 3 | do_loop_06.f90 | inject | Insert implicit_deallocate before exit only in block constructs |

## Test patterns

- **inject**: Test file added by the PR. Validator injects test into base workspace, builds, verifies failure. At fixed commit, test passes.
- **exists**: Test file already existed. The fix changes behavior. Validator runs existing test, verifies it fails at base, passes at fixed.

## Implementation Notes

### Build approach

LFortran requires a micromamba env (`lf-llvm11`) with LLVM 11 and other deps. Cannot build
from a fresh clone - must use the lfortran-dev meta-repo build infrastructure.

**Workspace model** (different from fortbench):
- Workspace = `lfortran-dev/lfortran/` directory (in-place, not a fresh clone)
- `git checkout {base_commit}` to switch to base, then incremental build
- Setup: `cd lfortran-dev && scripts/lf.sh build` (~2-3 min incremental)
- Agent works on C++ source files in `src/`
- Acceptance: `scripts/lf.sh itest -b llvm -t {test_name}` to run specific integration test

### Harness changes needed (vs fortbench)
- `clone_workspace()` → `checkout_workspace()` (git checkout in-place instead of clone)
- Pre-build cache: keep a warm build dir, only rebuild changed files
- Task isolation: `git checkout` + `git clean -fd src/` between tasks
- For "inject" tasks: copy test file from fixed commit before building

### Commits
- base_commit = parent of merge commit (`merge_sha^1`)
- fixed_commit = merge commit
- `scripts/verify_oracles.sh` checks that every fixed commit is a strict
  descendant of its base. Because the selected fixes come from one linear
  project history, a fixed commit may intentionally also be a later task's
  base; the script reports those overlaps for auditability.

### Rebuild behavior

The harness runs setup once for the baseline and again after every agent stage.
For LFortran, CMake/Ninja reuse the workspace build directory, so these are
incremental rebuilds that ensure each staged C++ patch is incorporated before
acceptance runs.

### Timeouts
- Build: ~120s incremental, ~300s if many files changed
- Test: ~5-30s per integration test
- Stage budget: 1800s (model needs time to understand C++ compiler code)
- Stagnation: 1800s

### Pre-testing status
- [x] All 20 merge commits exist and are reachable
- [x] All 20 base commits (^1) exist
- [x] All 20 PRs have C++ source changes in src/
- [x] All 20 PRs have integration test .f90 files
- [x] Build requires lfortran-dev meta-repo env (not standalone cmake)
- [ ] End-to-end oracle check per task (base fails, fixed passes)
