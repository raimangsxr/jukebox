# Implementation Plan: Contador de reinicio de límites en participación

**Branch**: `022-limit-reset-countdown` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-limit-reset-countdown/spec.md`

## Summary

Add **live MM:SS countdown** on `/participar` for **votes** (header) and **YouTube searches** (search subsection), showing time until **full quota** recovery. Replace rolling 10-minute windows with **fixed windows** starting at **first consumption at full quota**; server is authoritative via `*_quota_reset_at` timestamps on `GET /api/participant/state`. Client ticks countdown locally, auto-refreshes state at `00:00`. Requires Alembic migration (participant window columns + `participant_searches` table).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, existing SSE/`LiveConnectionManager`, TailwindCSS

**Storage**: PostgreSQL — new nullable `votes_quota_reset_at`, `searches_quota_reset_at` on `participants`; new `participant_searches` table; existing `votes` table for in-window vote counts

**Testing**: `backend/tests/test_limit_windows.py` + updates to `test_votes.py` / `test_youtube_search.py` / `test_participant_submit.py`; `limit-countdown.util.spec.ts`, `participant-limits.util.spec.ts`, `participate.component.spec.ts`; manual quickstart Phases 1–8; `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; participant `/participar`

**Project Type**: Web application (FastAPI + Angular SPA)

**Performance Goals**: Countdown tick client-side (1 Hz); state refresh at expiry < 3s; no extra SSE payload for limits (full refresh on poll/expiry)

**Constraints**: Spanish copy «Cupo completo en MM:SS»; fixed window (not rolling); searches persisted in DB (multi-replica safe); invalid vote/search does not start window

**Scale/Scope**: ~1 migration; 2 backend services refactored; shared limit-window helper; FE countdown util + participate template updates; ~300–400 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Draft `contracts/contract-deltas.md`; merge at implement |
| IV. Contract updates before implementation | Pass | Extend `ParticipantStateResponse` in deltas |
| V. Tests for changed behavior | Pass | Backend window tests + FE util specs + quickstart |
| VI. Sibling conventions | Pass | `/api/*`, Spanish UI, participant session |

**Post-design re-check**: All gates pass. Migration justified (search limit was in-memory; fixed windows need durable `*_quota_reset_at`).

## Project Structure

### Documentation (this feature)

```text
specs/022-limit-reset-countdown/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── contracts/contract-deltas.md
└── tasks.md                    # Phase 2 — /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/               # participants columns + participant_searches
├── app/
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   ├── limit_window_service.py   # shared fixed-window logic
│   │   ├── vote_service.py           # fixed window + reset_at
│   │   └── search_rate_limiter.py    # DB-backed or delegate to limit_window
│   └── routers/youtube.py
└── tests/
    ├── test_limit_windows.py
    ├── test_votes.py
    └── test_youtube_search.py

frontend/
├── src/app/
│   ├── models/jukebox-state.ts
│   ├── participant-limits.util.ts
│   ├── limit-countdown.util.ts       # format MM:SS, tick, expiry callback
│   ├── participate/participate.component.{ts,html}
│   └── services/participant-state.service.ts
```

**Structure Decision**: Shared `limit_window_service` for vote/search symmetry; persist search events in DB; expose reset instants on participant state only (not global SSE).

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- Fixed window from first full-quota consumption (replaces rolling)
- `votes_quota_reset_at` / `searches_quota_reset_at` on `Participant`
- `participant_searches` table for durable search counts
- Client derives MM:SS from ISO `*_quota_reset_at`; `refresh()` at expiry
- Copy: «X de Y votos disponibles · Cupo completo en MM:SS»

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`limit_window_service.py`**
   - `WINDOW = timedelta(minutes=10)` from settings
   - `start_window_if_full_quota(ends_at, consumed_in_window, max)` → new `ends_at` or existing
   - `quota_reset_at(now, ends_at)` → `None` if expired or unset
   - `remaining(max, used_in_window, now, ends_at)` → int

2. **Votes** (`vote_service.py`)
   - Load `participant.votes_quota_reset_at`
   - If expired: clear column, full quota
   - On `cast_vote` at full quota: set `votes_quota_reset_at = now + WINDOW`
   - `votes_remaining` = max − count(`Vote` where `created_at >= ends_at - WINDOW`)

3. **Searches**
   - Insert `participant_searches` row on allowed search
   - Same `searches_quota_reset_at` column pattern on `Participant`
   - Remove in-memory-only path for participant searches (keep operator bypass)

4. **`ParticipantStateResponse`** — add:
   - `searches_remaining: int`
   - `votes_quota_reset_at: datetime | null`
   - `searches_quota_reset_at: datetime | null`

5. **Tests** (`test_limit_windows.py`):
   - First vote at full quota starts window; second vote does not extend
   - Counter fields present after consume; null at full quota no window
   - Window expiry restores full quota
   - Search symmetry; invalid query does not insert row
   - Multi-tab: state endpoint returns same `*_quota_reset_at`

### Frontend design

1. **`limit-countdown.util.ts`**
   - `secondsUntil(isoEndsAt, now?)` 
   - `formatCountdownMmSs(seconds)` (canonical; do not alias as `formatMmSs`)
   - `shouldShowQuotaCountdown(resetAt)` — non-null and in future (server sets `reset_at` on first full-quota consume, clears on expiry)

2. **`participant-limits.util.ts`**
   - `votesRemainingLabel(remaining, max, resetAt?)` — append «· Cupo completo en MM:SS» when active
   - `searchesRemainingLabel(remaining, max, resetAt?)` — new

3. **`participate.component.ts`**
   - 1 Hz tick from `state.*_quota_reset_at`; `cdr.markForCheck()` each tick (OnPush)
   - On tick → `secondsUntil === 0` → `stateService.refresh()`
   - Show searches label in search subsection

4. **`participant-state.service.ts`**
   - On SSE `state` for participant: call `refresh()` (full state with limits) for multi-tab sync

5. **`jukebox-state.ts`** — extend `ParticipantStateResponse`

## Phase 2 — Tasks

See [tasks.md](./tasks.md) (34 tasks; post-analyze remediation applied).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Alembic migration | Durable `*_quota_reset_at` + search log | In-memory search limiter breaks fixed-window semantics and multi-replica deploys |
| New `participant_searches` table | Count searches in active window | Column-only counter loses audit trail on restart |
