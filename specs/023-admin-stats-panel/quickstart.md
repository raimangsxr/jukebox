# Quickstart: 023-admin-stats-panel

Validation after implementation.

## Prerequisites

- Branch `023-admin-stats-panel`
- Operator session on `/admin`
- Optional: 2+ dev participants with submissions/votes (dev auth on `/participar?dev=1`)

## Phase 1 — Panel placement and default state (US1, FR-001)

1. Open `/admin`
2. **Expected**: **Estadísticas** panel exists **after Historial**, **collapsed**; only Moderación expanded.

## Phase 2 — Load on expand (US1, FR-009)

1. Expand **Estadísticas**
2. **Expected**: Loading indicator, then summary totals (participantes, envíos, votos, canciones con votos)
3. **Expected**: No stats HTTP request while panel was collapsed (network tab)

## Phase 3 — Rankings accuracy (US2–US3, SC-003)

1. With known test data (e.g. participant A: 3 submissions, B: 5 votes on one song)
2. Expand Estadísticas
3. **Expected**: Top submitters/voters/songs match DB counts; max 10 rows; alphabetical tie-break at rank 10 if tested

## Phase 4 — Queue counters (US4, FR-008)

1. Create pending + queued + played entries
2. Refresh stats
3. **Expected**: `pending_review`, `queued`, `playing`, `played`, `rejected` match actual counts

## Phase 5 — Manual refresh only (US4, clarifications)

1. With panel expanded, cast a vote or submit from another tab
2. **Expected**: Stats **unchanged** until **Actualizar** or collapse+expand
3. Press **Actualizar**
4. **Expected**: Updated within ~3s (SC-004)

## Phase 6 — Vaciar historial (FR-011)

1. Note played/rejected counts and a song in top rankings from history
2. **Vaciar historial** (confirm)
3. **Actualizar** estadísticas
4. **Expected**: Played/rejected → 0; rankings/totals exclude deleted entries

## Phase 7 — Empty event (SC-005)

1. Fresh DB or no participant activity
2. Expand Estadísticas
3. **Expected**: Zeros and empty-state copy; no errors

## Phase 8 — Auth (FR-002)

1. `GET /api/admin/stats` without operator session → **401**
2. Participant dev session cannot access endpoint

## Phase 9 — Mobile layout (SC-002, FR-013)

1. On a standard mobile viewport, expand Estadísticas with full v1 data loaded
2. **Expected**: Section order Resumen → Estado de cola → rankings; entire v1 fits within **≤2 screen heights** of vertical scroll
3. **Expected**: All visible strings in Spanish (headings, «Actualizar», empty states)

## Automated

```bash
pytest backend/tests/test_admin_stats.py -q
npm --prefix frontend test -- src/app/admin/admin-stats.util.spec.ts
npm --prefix frontend run build
```

Manual Phases 1–9: constitution V sign-off.
