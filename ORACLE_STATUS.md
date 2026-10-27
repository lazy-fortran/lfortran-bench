# Oracle Verification Status

Candidate manifests prepared: 20/20

End-to-end oracle verification (base fails, fixed passes) is complete for the
five tasks changed by this change set and still pending for the other fifteen.

## Verified (base fails, fixed passes)

Each row was checked by building LFortran at both pinned commits and running
the task's validator against the resulting binary. The build reports its own
commit, so the binary is tied to the pinned commit it was built from.

| Task | Base | Fixed | Failure at base |
|---|---|---|---|
| lf-6943-findloc-2d-array | e98cfef6b (0.51.0-45) | 95ce13ca4 (0.51.0-46) | `ERROR STOP` from `intrinsics_374.f90` |
| lf-7039-extended-type-assign | 112a47ecb (0.51.0-157) | 23424c9e5 (0.51.0-161) | `asr_to_llvm: module failed verification`, stored value type does not match pointer operand type |
| lf-7222-operator-overload-multi | 87e8923ca (0.52.0-66) | 2443204f0 (0.52.0-69) | `LCOMPILERS_ASSERT` `left_type2->type < 7`, `src/lfortran/semantics/asr_implicit_cast_rules.h:602` |
| lf-8312-common-block-use | 3785cf907 (0.55.0-7) | 724e06adc (0.55.0-8) | `LCOMPILERS_ASSERT` `scope.find(name) == scope.end()`, `src/libasr/asr_scopes.h:85` |
| lf-8421-string-bindc | 1900e28db (0.56.0-110) | d8d25738b (0.56.0-120) | `LCOMPILERS_ASSERT` "Unmatching String Physical Types", `src/libasr/codegen/asr_to_llvm.cpp:11031` |

## Candidates (15 task manifests ready)

- lf-5987-implicit-dealloc-exit
- lf-7100-classtype-polymorphic
- lf-7900-externalsym-binop
- lf-8041-parameter-expr-eval (replaced lf-8100)
- lf-8150-optional-nested
- lf-8345-implied-do-param
- lf-8352-string-alloc-temp
- lf-8401-array-constructor-verify
- lf-8405-reshape-cast
- lf-8409-select-type-member
- lf-8412-string-nullify
- lf-8431-array-reshape
- lf-8481-complex-array-member
- lf-8490-elemental-array-derived
- lf-8511-read-format-literal (replaced lf-8437)
