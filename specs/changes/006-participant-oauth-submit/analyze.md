# Analysis: 006-participant-oauth-submit

**Date**: 2026-07-18  
**Status**: Remediated — all issues from initial analyze pass resolved in spec/plan/tasks/contracts/quickstart

## Initial findings (resolved)

| ID | Severity | Summary | Resolution |
|----|----------|---------|------------|
| I1 | HIGH | MVP T001–T022 excluded P1 US4 (vote regression) | MVP updated to **T001–T029**; US4 before US3 in incremental delivery |
| C1 | MEDIUM | SC-005 disabled controls not explicit in T015 | T015 + contract-deltas: vote/submit disabled when unauthenticated; quickstart Phase 1 step 2 |
| C2 | MEDIUM | Concurrent submit edge case untested | Added to T017 + quickstart Phase 3 step 6 |
| C3 | MEDIUM | oEmbed/private video failure underspecified | T017/T018 + quickstart Phase 3 step 4 |
| C4 | MEDIUM | US4 SSE acceptance only backend | T029 SSE verification; quickstart Phase 4 step 4 |
| A1 | MEDIUM | Spanish API vs UI error ambiguity | Spec clarification + contract-deltas mapping table; T021 `mapSubmitError` |
| I2 | MEDIUM | Dev-auth demoted vs hidden in production | T015 + research/contracts: hide unless dev flag or `?dev=1` |
| U1 | MEDIUM | T023 ambiguous test file | Fixed to `test_participant_submissions.py` |
| C5 | LOW | Re-submit after played/reject untested | Added to T017 + quickstart Phase 3 steps 7–8 |
| C6 | LOW | T009 omitted submissions route | T009 includes `GET /api/participant/submissions` |
| C7 | LOW | FR-012 operator regression manual only | T033 + quickstart Phase 5 expanded (acceptable per Constitution V) |
| A2 | LOW | SC-001/SC-002 no automated tasks | quickstart Phase 1 (SC-001) and Phase 4 (SC-002) timing steps; T033 references |

## Post-remediation metrics

| Metric | Value |
|--------|-------|
| Critical issues | 0 |
| High issues | 0 (1 resolved) |
| Medium issues | 0 (7 resolved) |
| FR coverage | 13/13 |
| SC coverage | 5/5 (3 automated, 2 manual via T033/quickstart) |
| Total tasks | 35 (T001–T035) |

## Gate status

| Step | Status |
|------|--------|
| `/speckit.specify` | Done |
| `/speckit.plan` | Done |
| `/speckit.tasks` | Done (remediated) |
| `/speckit.analyze` | Done — clear to implement |
| `/speckit.implement` | **Done** |

## Notes

- Constitution IV: T002–T003 must complete before implementation code.
- API errors: English stable `detail`; Spanish in `/participar` UI only.
- Re-run `/speckit.analyze` after further spec edits if scope changes.
