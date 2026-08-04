# Research: 023-admin-stats-panel

**Feature**: `023-admin-stats-panel`  
**Date**: 2026-08-04

## R1 — API shape: dedicated stats endpoint vs client-side aggregation

**Decision**: Single operator endpoint `GET /api/admin/stats` returning a pre-aggregated `AdminStatsResponse`.

**Rationale**: Rankings require SQL `GROUP BY`, tie-break ordering, and joins to `participants`; doing this in the browser would require downloading large lists (history, votes, submissions) and duplicate business rules. One round-trip on panel expand matches FR-009 and SC-004.

**Alternatives considered**:
- Reuse multiple existing endpoints (`/history`, `/pending`, participant lists) — rejected: no vote rankings, heavy client merge, inconsistent tie-break.
- SSE push of stats — rejected per clarification (no auto-refresh while open).

## R2 — Vote totals for «canciones más votadas»

**Decision**: Aggregate **`SUM(queue_entries.vote_count)` grouped by `youtube_video_id`**, using the latest non-empty `title` for display; only rows with `vote_count > 0`.

**Rationale**: `vote_count` is the denormalized total per queue entry; summing across entries with the same video id matches spec FR-006. Using the `votes` table alone would require join + group by video id and matches the same result when consistent.

**Alternatives considered**:
- Per queue entry ranking — rejected: spec requires merge by video id.
- Materialized stats table — rejected: over-engineering for v1; live query sufficient at event scale.

## R3 — «Ha participado» participant count

**Decision**: `COUNT(DISTINCT participant_id)` over the union of:
- `queue_entries.submitted_by_participant_id IS NOT NULL`
- `votes.participant_id`

**Rationale**: Matches FR-003 and clarification (submission OR vote). Login alone does not count.

## R4 — Top-10 tie-break

**Decision**: SQL `ORDER BY count DESC, display_name ASC` (participants) or `ORDER BY vote_total DESC, title ASC` (songs) with `LIMIT 10`.

**Rationale**: Implements clarification A — max 10 rows, alphabetical tie-break at position 10.

## R5 — Refresh UX

**Decision**: Frontend fetches stats when `CollapsibleSection` expands (`expandedChange` true) and on **Actualizar** button; no fetch while collapsed; no SSE subscription for stats.

**Rationale**: Matches clarification B; avoids background load on admin page.

## R6 — Placement in Admin accordion

**Decision**: New panel id `stats` inserted **after `history`** and before `reserve`; default `panelExpanded.stats = false`.

**Rationale**: Spec assumption; retrospective metrics sit naturally after historial.

## R7 — Migration

**Decision**: **No migration** — read-only aggregates over existing `participants`, `queue_entries`, `votes`.

**Rationale**: No new persisted entities; stats reflect current DB rows (including post-`DELETE /api/queue/history` state per FR-011).
