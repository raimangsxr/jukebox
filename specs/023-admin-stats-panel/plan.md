# Implementation Plan: Panel de estadísticas en Admin

**Branch**: `023-admin-stats-panel` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/023-admin-stats-panel/spec.md`

## Summary

Add a collapsed **Estadísticas** accordion panel on `/admin` (after Historial) showing participation totals, queue status counts, and top-10 rankings (submitters, voters, most-voted songs). New operator endpoint **`GET /api/admin/stats`** returns pre-aggregated `AdminStatsResponse`. Stats load **on panel expand** and via **Actualizar** only — no SSE or polling. **No database migration** (read-only SQL over `participants`, `queue_entries`, `votes`).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, existing `CollapsibleSectionComponent`, TailwindCSS, operator session auth (`CurrentUser`)

**Storage**: PostgreSQL — existing tables only; aggregates computed at query time

**Testing**: `backend/tests/test_admin_stats.py`; optional `admin-stats.util.spec.ts`; manual [quickstart.md](./quickstart.md); `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; operator `/admin`

**Project Type**: Web application (FastAPI + Angular SPA)

**Performance Goals**: Stats response < 3s on local network (SC-004); single query batch per section acceptable for event-scale data

**Constraints**: Spanish UI; operator-only; max 10 ranking rows with alphabetical tie-break; stats reflect current DB rows (post clear-history); no background fetch while collapsed

**Scale/Scope**: ~1 new router, 1 service, 4–5 schemas; admin panel + service; ~400–500 LOC; **no Alembic migration**

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | `contracts/contract-deltas.md`; merge at implement |
| IV. Contract updates before implementation | Pass | Document `GET /api/admin/stats` + admin panel |
| V. Tests for changed behavior | Pass | `test_admin_stats.py` + quickstart manual |
| VI. Sibling conventions | Pass | `/api/*`, operator session, Spanish UI |

**Post-design re-check**: All gates pass. No migration; no new persisted entities.

## Project Structure

### Documentation (this feature)

```text
specs/023-admin-stats-panel/
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
├── app/
│   ├── schemas.py              # AdminStatsResponse, ranking DTOs
│   ├── services/stats_service.py
│   ├── routers/admin_stats.py  # GET /api/admin/stats
│   └── main.py                 # register router
└── tests/test_admin_stats.py

frontend/
├── src/app/
│   ├── models/admin-stats.ts
│   ├── services/admin-stats.service.ts
│   └── admin/
│       ├── admin.component.{ts,html}
│       └── admin-stats.util.ts   # optional: labels/empty-state helpers (extract if reused)
```

**Structure Decision**: Dedicated `stats_service` keeps aggregation testable; thin router; frontend service mirrors other admin API clients.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- `GET /api/admin/stats` with `AdminStatsResponse`
- `SUM(vote_count)` by `youtube_video_id` for song rankings
- Distinct participant union (submissions ∪ votes) for active count
- `ORDER BY count DESC, name/title ASC LIMIT 10`
- Fetch on expand + Actualizar; panel after Historial
- No migration

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`stats_service.py`**
   - `build_admin_stats_response(db: Session) -> AdminStatsResponse`
   - `_queue_status_counts(db)` — `GROUP BY status`
   - `_top_submitters(db, limit=10)` — join `participants`, filter `submitted_by_participant_id IS NOT NULL`
   - `_top_voters(db, limit=10)` — `GROUP BY votes.participant_id`
   - `_top_songs(db, limit=10)` — `GROUP BY youtube_video_id`, `HAVING SUM(vote_count) > 0`
   - `_participants_active_count(db)` — union distinct ids
   - `_distinct_voted_songs_count(db)`

2. **`routers/admin_stats.py`**
   - `GET /api/admin/stats` — `CurrentUser`, returns `build_admin_stats_response(db)`

3. **Schemas** — `AdminStatsResponse`, `QueueStatusCounts`, `ParticipantRankingItem`, `SongRankingItem`

### Frontend design

1. Extend `AdminPanelId` with `'stats'`; `panelExpanded.stats = false`
2. Insert `<app-collapsible-section title="Estadísticas">` after Historial block in `admin.component.html`
3. `AdminStatsService.getStats()` → `GET /api/admin/stats`
4. On `setPanelExpanded('stats', true)` → `loadStats()` only when expanding; **Actualizar** calls same `loadStats()` with shared loading/error; **no fetch while collapsed**
5. Template section order: **Resumen → Estado de cola → rankings**; compact for SC-002 (≤2 mobile viewport heights)
6. Loading/error flags + `markForCheck()` (OnPush)

### User story mapping

| Story | Delivery |
|-------|----------|
| US1 Resumen | Summary fields in `AdminStatsResponse` + expand fetch |
| US2 Rankings participantes | `top_submitters`, `top_voters` |
| US3 Canciones más votadas | `top_songs` |
| US4 Contadores cola | `queue_counts` + Actualizar |

## Complexity Tracking

No constitution violations.

## Next steps

1. `/speckit-tasks` — task breakdown
2. `/speckit-implement` — merge contracts, implement endpoint + panel, tests
