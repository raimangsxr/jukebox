# Analysis: 010-hardening-and-polish

**Date**: 2026-07-22
**Status**: remediated
**Artifacts analyzed**: [spec.md](./spec.md), [plan.md](./plan.md), [tasks.md](./tasks.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md)

## Method

Cross-checked every functional requirement (FR-001…FR-031) against tasks (T001…T057) and contract deltas; checked every success criterion (SC-001…SC-011) for a validating task; checked spec↔plan↔tasks↔contract consistency; looked for ambiguities, missing data paths, and duplicate/conflicting tasks.

## Findings (pre-remediation)

| ID | Severity | Summary | Resolution |
|----|----------|---------|------------|
| A1 | **MEDIUM** | FR-019 requires applying `event_config.theme` on `/participar`, but no endpoint delivers event config to participant clients (`ParticipantStateResponse` lacks it) — the requirement was unimplementable as written. | Added `theme` to `ParticipantStateResponse` in `contract-deltas.md`; added clause to **FR-019**; added task **T057** (backend) and made **T040** participant part depend on it. |
| A2 | LOW | SC-003 ("event loop not blocked") had no dedicated automated assertion — only regression tests on search/OAuth (T016/T017) after the async migration. A strict, non-flaky concurrency assertion is hard to write. | Documented explicitly; added a manual responsiveness check under concurrent searches to the quickstart scope (**T054**). Async migration (T018–T020) is the substantive fix. |
| A3 | LOW | T028 (`0007`) and T032 (`0008`) both edit `backend/app/models.py`; risk of a merge conflict if worked in parallel. | `tasks.md` Notes and Parallel-opportunities call out coordinating shared-file edits; the two migrations sit in the same story (US4) and run sequentially. No change needed beyond the existing note. |
| A4 | LOW | `data-model.md` referenced by the flow was not authored; migrations/entities are instead described in `contract-deltas.md` (Migrations table + Key Entities in spec). | Accepted: the two migrations and the (no-migration) event-config are fully specified in `contract-deltas.md`; a separate `data-model.md` would duplicate it. Noted here so the omission is intentional, not a gap. |
| A5 | INFO | Some FRs/SCs contain implementation detail (async client, `replicas:1`, bundle budget). | Accepted deviation for a remediation change; recorded in `checklists/requirements.md` (`[~]` items). |

## Requirements coverage (post-remediation)

**31 / 31 functional requirements** have at least one implementing task.

| FR group | FRs | Tasks |
|----------|-----|-------|
| SSE isolation | FR-001…FR-004 | T004, T005, T007, T008, T009, T010, T011 |
| Secrets / CORS / token | FR-005…FR-008 | T012, T013, T014, T015, T028, T029, T023 |
| Robustness | FR-009…FR-014 | T016–T022, T030, T031, T032, T033, T024, T025, T026, T027 |
| Event config | FR-015…FR-019 | T034, T035, T036, T037, T038, T039, T040, T057 |
| Frontend polish | FR-020…FR-024 | T041, T042, T043, T044, T045 |
| Tests & hygiene | FR-025…FR-031 | T007/T008/T023–T027/T034 (backend), T036/T047/T048/T049 (frontend), T046, T051, T052, T053, T050, T055 |

## Success-criteria coverage

| SC | Validated by |
|----|--------------|
| SC-001 isolation (0 leaks) | T007, T008 |
| SC-002 `.env` untracked | T012 |
| SC-003 event loop not blocked | T018–T020 (fix) + T054 manual check *(no automated assertion — A2)* |
| SC-004 ≤1 hash comparison | T023 |
| SC-005 config reflected on kiosk | T034, T037, T039, T040 + T054 |
| SC-006 kiosk no clipping 720p–4K | T041 + T054 |
| SC-007 per-row moderation | T036, T042 |
| SC-008 bundle within budget | T044 |
| SC-009 tests pass (added coverage) | T047–T050 |
| SC-010 contracts/manifest consistent | T051, T052, T053 |
| SC-011 regression 001–009 | T050, T055 |

## Consistency check

- User stories, priorities (P1/P2/P3), and phase grouping match across `spec.md`, `plan.md`, and `tasks.md`. ✅
- Every behavior-changing FR has a corresponding entry in `contract-deltas.md` (SSE routing, `event-config` endpoints, participant `theme`, token prefix, submit validation, FK, CORS, `replicas:1`). ✅
- Non-Goals in `spec.md` (no review-section-4 features, no Redis/multi-replica) are reflected in `plan.md` Complexity Tracking (single-replica justified). ✅
- Manifest (`010` draft, active) and `AGENTS.md` updated; contracts to be reconciled at implement time (T001 merge, T051 reconcile). ✅

## Post-remediation metrics

- Requirements coverage: **100%** (31/31 FR with tasks)
- Success criteria: **11/11** covered (SC-003 via manual quickstart step)
- Critical/High issues: **0**
- Medium issues: **0 open** (A1 remediated)
- Total tasks: **57** (T001–T057)

## Gate

**Ready for `/speckit.implement`.** Recommended first increment: Setup + Foundational → **US1 (SSE isolation)** → **US2 (secrets)**, validating each P1 story before proceeding. Note the operational prerequisites in US2 (session-secret rotation and one-time embed/API token reissue) must be scheduled with the operator before production rollout.
