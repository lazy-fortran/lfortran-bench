# lfortran-bench

Compiler development benchmark for AI coding agents, targeting the LFortran compiler.

**Status: Work in Progress**

The 20 task manifests are candidates. End-to-end base-fails/fixed-passes
oracle verification is still pending; see [ORACLE_STATUS.md](ORACLE_STATUS.md).

License: [MIT](LICENSE)

## Goal

Assess the suitability of local and cloud AI coding models for compiler development tasks.
Uses resolved LFortran issues (closed before September 2025) with deterministic acceptance
checks based on integration tests and reference outputs.

## Design

- 20 benchmark tasks from the LFortran compiler (C++ codebase)
- Each task: a frozen base commit with a failing test + a known fixed commit
- Three-stage self-review repair loop (same protocol as [fortbench](https://github.com/lazy-fortran/fortbench))
- Deterministic acceptance: build LFortran, run the specific test, check output
- No regression testing (full test suite too slow for benchmark loop)

## Task selection criteria

- Issues closed before September 2025 (pre-vibe-coding era)
- Clear test case (integration test or reference test)
- Fix is 1-5 files, achievable in under 1 hour
- Builds incrementally on macOS with cmake/ninja + LLVM
- Variety: parser, semantics, ASR passes, codegen fixes

## Related projects

- [fortbench](https://github.com/lazy-fortran/fortbench): Fortran ecosystem coding benchmark (same harness)
- [devstral-infra](https://github.com/krystophny/devstral-infra): llama.cpp server management and model quiver
