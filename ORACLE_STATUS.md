# Oracle Verification Status

Verified: 18/20

## PASS (18 tasks ready)
- lf-5987-implicit-dealloc-exit
- lf-6943-findloc-2d-array
- lf-7039-extended-type-assign
- lf-7100-classtype-polymorphic
- lf-7222-operator-overload-multi
- lf-7900-externalsym-binop
- lf-8150-optional-nested
- lf-8312-common-block-use (new)
- lf-8345-implied-do-param
- lf-8352-string-alloc-temp
- lf-8401-array-constructor-verify
- lf-8405-reshape-cast
- lf-8409-select-type-member
- lf-8412-string-nullify
- lf-8421-string-bindc
- lf-8431-array-reshape
- lf-8481-complex-array-member
- lf-8490-elemental-array-derived

## FAIL (2 tasks need replacement)
- lf-8100-allocatable-print (segfault at both base and fixed - fix incomplete)
- lf-8437-struct-alloc-assign (runtime error at both - fix depends on other PRs)
