# Research: 022-limit-reset-countdown

**Date**: 2026-08-04

## R1 — Window semantics: rolling vs fixed

**Decision**: **Fixed window** starting when participant consumes first unit at **full quota**; window duration = existing 10-minute setting; additional consumptions in the same window do **not** extend `*_quota_reset_at`.

**Rationale**: Spec FR-001/FR-002 and clarification session explicitly require predictability («recuperar el cupo completo» at a single instant). Rolling windows (current `vote_service.count_votes_in_window` with `now - 10min`) produce staggered partial recovery incompatible with «Cupo completo en MM:SS».

**Alternatives considered**:
- Keep rolling, show countdown to oldest event expiry → rejected (user asked fixed start at first spend at max)
- Per-unit TTL per vote/search → rejected (scope; not «total recovery»)

## R2 — Persisting vote window anchor

**Decision**: Add nullable `participants.votes_quota_reset_at` (timestamptz UTC). In-window usage derived from `votes` rows with `created_at >= votes_quota_reset_at - WINDOW`.

**Rationale**: Votes already persisted; anchor column is minimal. Clearing column when `now >= votes_quota_reset_at` on read keeps idempotent expiry.

**Alternatives considered**:
- New `participant_limit_windows` table → rejected (overkill for two scalars)
- Derive only from first vote timestamp without column → rejected (ambiguous after expiry until next vote)

## R3 — Persisting search limits

**Decision**: Replace in-memory `search_rate_limiter` for participants with:
- `participants.searches_quota_reset_at`
- `participant_searches` table (`participant_id`, `created_at`) one row per **successful** quota-consuming search

**Rationale**: In-memory deque is not durable across restarts/replicas (010-hardening noted memory sweep only). Fixed window requires consistent `searches_remaining` and `searches_quota_reset_at` on `GET /participant/state`.

**Alternatives considered**:
- Keep in-memory + expose countdown only on same pod → rejected (violates FR-007 multi-tab/reload coherence)
- Redis → rejected (no Redis in stack)

## R4 — API shape for client countdown

**Decision**: Extend `ParticipantStateResponse` with:
- `searches_remaining: int`
- `votes_quota_reset_at: string | null` (ISO 8601)
- `searches_quota_reset_at: string | null`

Client computes `MM:SS` locally via `formatCountdownMmSs`; calls `refresh()` when `secondsUntil(reset_at) <= 0`. On **every** participant SSE `state` event, call `refresh()` (not partial merge) so multi-tab tabs sync limits immediately.

**Rationale**: Server clock authority without per-second polling. Matches SC-003/SC-004 (≤2s skew after sync). Fixes multi-tab gap where SSE merge omitted limit fields.

**Alternatives considered**:
- `votes_reset_in_seconds` integer only → rejected (client clock drift without periodic resync)
- Push countdown via SSE every second → rejected (chatty)

## R5 — UI placement and copy

**Decision**: Per clarifications:
- Votes: header inline «X de Y votos disponibles · Cupo completo en MM:SS»
- Searches: subsection «X de Y búsquedas disponibles · Cupo completo en MM:SS»
- Hide countdown clause when `*_quota_reset_at` is null

**Rationale**: Locked in spec clarifications 2026-08-04.

**Alternatives considered**: N/A

## R6 — Auto-refresh at 00:00 and multi-tab sync

**Decision**: `participate.component` 1 Hz tick with `markForCheck()`; when countdown hits 0, `ParticipantStateService.refresh()` (FR-014). On **every** participant SSE `state` event, `participant-state.service` calls `refresh()` instead of merging queue-only fields.

**Rationale**: Expiry refresh meets SC-006; SSE refresh meets US3 sc.2 without 15s poll delay.

**Alternatives considered**:
- Wait for SSE/poll only → rejected (clarification A + multi-tab requirement)
- Partial SSE merge of limit fields → rejected (SSE payload lacks participant limits)
