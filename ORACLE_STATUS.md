# Oracle Verification Status

<<<<<<< HEAD
Candidate manifests prepared: 20/20

End-to-end oracle verification (base fails, fixed passes) is still pending.

## Candidates (20 task manifests ready)
=======
Verified: 20/20 (after fixes)

## PASS (13 tasks, verified in initial oracle run)
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks)
- lf-5987-implicit-dealloc-exit
- lf-7100-classtype-polymorphic
- lf-7900-externalsym-binop
- lf-8041-parameter-expr-eval (replaced lf-8100)
- lf-8150-optional-nested
- lf-8200-struct-implied-do
- lf-8345-implied-do-param
- lf-8352-string-alloc-temp
- lf-8373-select-type-associate
- lf-8390-nested-struct-global
- lf-8401-array-constructor-verify
- lf-8405-reshape-cast
- lf-8409-select-type-member
- lf-8412-string-nullify
- lf-8421-string-bindc
- lf-8431-array-reshape
- lf-8481-complex-array-member
- lf-8490-elemental-array-derived
<<<<<<< HEAD
- lf-8504-complex-implicit-cast
- lf-8511-read-format-literal (replaced lf-8437)
=======

## FIXED - validator bugs corrected (3 tasks)
- lf-8100-allocatable-print (force-inject to overwrite stale workspace files)
- lf-8421-string-bindc (added missing C file injection and dual-file compilation)
- lf-8437-struct-alloc-assign (force-inject to overwrite stale workspace files)

## REPLACED - base-passes tasks swapped for new PRs (4 tasks)
- lf-8200-struct-implied-do -> lf-6943-findloc-2d-array (PR #6943)
- lf-8373-select-type-associate -> lf-7039-extended-type-assign (PR #7039)
- lf-8390-nested-struct-global -> lf-7222-operator-overload-multi (PR #7222)
- lf-8504-complex-implicit-cast -> lf-7399-move-alloc-dealloc (PR #7399)
>>>>>>> e506e86 (fix: repair 7 broken task validators, replace 4 base-passes tasks)
