# Analysis Remediation: 018-filler-reserve-csv

**Date**: 2026-08-04  
**Source**: `/speckit-analyze` findings I1–U7

| ID | Resolution |
|----|------------|
| I1 | FR-007 + clarification updated: validate within-file dupes + active queue only; not current reserve rows |
| I2 | tasks.md reordered: US1 export Phase 2 after Setup only; import foundation Phase 3 blocks US2/US3 |
| U1 | T009 + plan + contract: `Content-Disposition` dated filename |
| U2 | T011 GET list after import; T016 `refreshReserve()`; quickstart FR-011 |
| U3 | T011 SC-006 API tests; T015a detail codes; quickstart Phase 2 SC-006 |
| U4 | T010 no longer `[P]` with T007; depends on T009 |
| U5 | Contract deltas: stable `detail` code table |
| U6 | T007: UTF-8 BOM assertion |
| D1 | FR-006 references FR-007 for validation scope (deduped prose) |
| U7 | spec edge case: last-write-wins, no optimistic lock v1 |

**Status**: All analyze findings addressed. Implementation complete (2026-08-04).
