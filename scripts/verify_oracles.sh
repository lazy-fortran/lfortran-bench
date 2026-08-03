#!/usr/bin/env bash
# Verify oracle for all tasks: base should FAIL, fixed should PASS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORK_DIR="/tmp/lfortran-oracle-verify"
CONDA_ENV="lf-llvm11"
CMAKE_ARGS="-G Ninja -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DWITH_LLVM=yes -DCMAKE_BUILD_TYPE=Debug -DWITH_ZSTD=no -DWITH_ZLIB=no -DWITH_RUNTIME_STACKTRACE=yes"

rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

# Clone once
echo "Cloning lfortran..."
git clone https://github.com/lfortran/lfortran.git "${WORK_DIR}/lfortran"

# Pre-fetch all needed commits upfront, storing as real refs
echo "Pre-fetching all task commits..."
for td in "${REPO_ROOT}"/tasks/pilot/*/; do
    ty="${td}/task.yaml"
    [ -f "$ty" ] || continue
    fc=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['fixed_commit'])")
    bc=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['base_commit'])")
    git -C "${WORK_DIR}/lfortran" fetch origin "${fc}:refs/bench/${fc}" 2>/dev/null || echo "  WARN: could not fetch ${fc}"
    git -C "${WORK_DIR}/lfortran" fetch origin "${bc}:refs/bench/${bc}" 2>/dev/null || echo "  WARN: could not fetch ${bc}"
done
echo "Pre-fetch done."

echo "Checking task commit relationships..."
declare -A BASE_OWNERS
for td in "${REPO_ROOT}"/tasks/pilot/*/; do
    ty="${td}/task.yaml"
    [ -f "$ty" ] || continue
    task_id=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['id'])")
    bc=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['base_commit'])")
    BASE_OWNERS["$bc"]="${BASE_OWNERS[$bc]:-} ${task_id}"
done

PREFLIGHT_FAILED=0
for td in "${REPO_ROOT}"/tasks/pilot/*/; do
    ty="${td}/task.yaml"
    [ -f "$ty" ] || continue
    task_id=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['id'])")
    fc=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['fixed_commit'])")
    bc=$(python3 -c "import yaml; print(yaml.safe_load(open('${ty}'))['base_commit'])")
    if [ "$bc" = "$fc" ]; then
        echo "  ERROR: ${task_id} has identical base and fixed commits"
        PREFLIGHT_FAILED=1
    elif ! git -C "${WORK_DIR}/lfortran" merge-base --is-ancestor "$bc" "$fc"; then
        echo "  ERROR: ${task_id} fixed commit is not downstream of its base"
        PREFLIGHT_FAILED=1
    fi
    if [ -n "${BASE_OWNERS[$fc]:-}" ]; then
        echo "  NOTE: ${task_id} fixed commit is also a base for:${BASE_OWNERS[$fc]}"
    fi
done
if [ "$PREFLIGHT_FAILED" -ne 0 ]; then
    rm -rf "${WORK_DIR}"
    exit 1
fi

PASS=0
FAIL=0
ERRORS=""

for task_dir in "${REPO_ROOT}"/tasks/pilot/*/; do
    task_yaml="${task_dir}/task.yaml"
    validate_py="${task_dir}/validate.py"
    [ -f "$task_yaml" ] || continue
    [ -f "$validate_py" ] || continue

    task_id=$(python3 -c "import yaml; print(yaml.safe_load(open('${task_yaml}'))['id'])")
    base=$(python3 -c "import yaml; print(yaml.safe_load(open('${task_yaml}'))['base_commit'])")
    fixed=$(python3 -c "import yaml; print(yaml.safe_load(open('${task_yaml}'))['fixed_commit'])")

    echo ""
    echo "=== ${task_id} ==="
    echo "  base:  ${base}"
    echo "  fixed: ${fixed}"

    cd "${WORK_DIR}/lfortran"

    # Test FIXED commit (should PASS)
    echo "  [fixed] checkout + build..."
    git checkout -f "${fixed}" --quiet 2>/dev/null || { echo "  ERROR: cannot checkout fixed ${fixed}"; ERRORS="${ERRORS}\n${task_id}: cannot checkout fixed"; continue; }
    git clean -fdx --quiet 2>/dev/null
    if ! conda run -n "${CONDA_ENV}" bash -c "cd ${WORK_DIR}/lfortran && bash build0.sh && cmake -S . -B build ${CMAKE_ARGS} && ninja -C build" >/dev/null 2>&1; then
        echo "  ERROR: fixed commit does not build"
        ERRORS="${ERRORS}\n${task_id}: fixed does not build"
        continue
    fi
    if python3 "${validate_py}" "${WORK_DIR}/lfortran" >/dev/null 2>&1; then
        echo "  [fixed] PASS (expected)"
    else
        echo "  [fixed] FAIL (UNEXPECTED - oracle broken!)"
        ERRORS="${ERRORS}\n${task_id}: fixed fails validation"
        continue
    fi

    # Test BASE commit (should FAIL)
    echo "  [base] checkout + build..."
    git checkout -f "${base}" --quiet 2>/dev/null || { echo "  ERROR: cannot checkout base ${base}"; ERRORS="${ERRORS}\n${task_id}: cannot checkout base"; continue; }
    git clean -fdx --quiet 2>/dev/null
    if ! conda run -n "${CONDA_ENV}" bash -c "cd ${WORK_DIR}/lfortran && bash build0.sh && cmake -S . -B build ${CMAKE_ARGS} && ninja -C build" >/dev/null 2>&1; then
        echo "  [base] BUILD FAIL (may be expected for old commits)"
        echo "  WARNING: base does not build - task may not be usable"
        ERRORS="${ERRORS}\n${task_id}: base does not build"
        continue
    fi
    if python3 "${validate_py}" "${WORK_DIR}/lfortran" >/dev/null 2>&1; then
        echo "  [base] PASS (UNEXPECTED - oracle broken! base should fail)"
        ERRORS="${ERRORS}\n${task_id}: base passes validation (oracle broken)"
        continue
    else
        echo "  [base] FAIL (expected)"
    fi

    echo "  ORACLE OK"
    PASS=$((PASS + 1))
done

echo ""
echo "=== SUMMARY ==="
echo "Passed: ${PASS}/20"
if [ -n "${ERRORS}" ]; then
    echo "Errors:"
    echo -e "${ERRORS}"
fi

rm -rf "${WORK_DIR}"
if [ -n "${ERRORS}" ]; then
    exit 1
fi
