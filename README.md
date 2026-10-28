# lfortran-bench

A benchmark of compiler-development tasks for AI coding agents, built from bugs
fixed in the [LFortran](https://github.com/lfortran/lfortran) compiler (C++).

Status: work in progress. All 20 task definitions exist; 5 have been checked to
fail at the base commit and pass at the fixed commit, the other 15 not yet (see
[ORACLE_STATUS.md](ORACLE_STATUS.md)).

## Design

- 20 tasks taken from LFortran pull requests merged before September 2025, each
  with a clear integration or reference test and a fix touching 1 to 5 files.
- Each task pins a base commit where the test fails and the commit that fixed it.
  The agent starts from the base commit and the issue description.
- Acceptance is deterministic: build LFortran, run the task's test, compare the
  output. The full LFortran test suite is not run, so regressions elsewhere are not
  detected.
- Up to three fresh agent invocations per task (attempt, self-review and repair,
  final repair), using the same harness as
  [fortbench](https://github.com/lazy-fortran/fortbench).
- Tasks cover the parser, semantic analysis, ASR passes and code generation; see
  [TASKS.md](TASKS.md).

## Requirements

- Python 3.11 or newer
- A conda environment named `lf-llvm11` with clang, CMake, Ninja and the LLVM
  development files needed to build LFortran; the task setup commands build
  LFortran inside it
- One supported agent CLI (OpenCode, Qwen Code, Claude Code, Codex or aider)

## Install and use

```bash
git clone https://github.com/lazy-fortran/lfortran-bench.git
cd lfortran-bench
python3 -m pip install -e .
```

Check that one task's acceptance test fails at the base commit and passes at the
fix:

```bash
lfortran-bench check-task tasks/pilot/lf-6943-findloc-2d-array/task.yaml
```

`scripts/verify_oracles.sh` performs this check for all tasks. Agents are run with
`lfortran-bench run-suite SUITE.yaml --output-dir runs/NAME`, where the suite file
lists the task manifests and the agent/model rows to run. No suite file is
included yet.

Run the unit tests with `python3 -m unittest discover -s tests`.

## Related projects

- [fortbench](https://github.com/lazy-fortran/fortbench): benchmark of Fortran
  library repair tasks with the same harness.

## License

MIT. See [LICENSE](LICENSE).
