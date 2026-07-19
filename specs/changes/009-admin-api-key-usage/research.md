# Research: 009-admin-api-key-usage

**Date**: 2026-07-19

## Decision: PostgreSQL persistence for daily counters

**Decision**: Alembic migration `0006` with table `youtube_api_key_daily_usage` storing per-key `used_count` for the Pacific `quota_day`.

**Rationale**: FR-007 requires survival across process restarts; constitution stack is PostgreSQL; operator needs trustworthy totals during events.

**Alternatives considered**:
- In-memory only (008 pool style) — rejected (fails FR-007)
- Redis — rejected (not in stack; YAGNI for 4–5 keys)

## Decision: Stable key identity via SHA-256 hash

**Decision**: `key_hash = sha256(raw_api_key).hexdigest()` as DB primary identity; display order from current `JUKEBOX_YOUTUBE_API_KEYS` list index.

**Rationale**: Keys may be reordered in env; hash stays stable; full secret never stored or returned.

**Alternatives considered**:
- Config index only — rejected (reorder breaks continuity)
- Store last-4 suffix — rejected (collision risk)

## Decision: Attempt-based increment before HTTP send

**Decision**: `record_attempt(db, key)` runs immediately before `urllib` outbound call; increments regardless of success/failure (clarify Q1).

**Rationale**: Matches spec clarification; aligns with Google quota consumption on failed calls.

**Alternatives considered**:
- Increment on 2xx only — rejected (clarified)

## Decision: Google quota-exhausted → display 100/0

**Decision**: `mark_google_exhausted` sets `used_count=100`, `exhausted=true` even if local count was lower (clarify Q2).

**Rationale**: Operator sees consistent exhausted state; pool `mark_exhausted` unchanged.

## Decision: SSE on existing `/api/events/stream`

**Decision**: New event type `api_key_usage` with payload `ApiKeyUsageListResponse` (full snapshot). Broadcast on increment, exhaustion, and quota-day roll.

**Rationale**: Clarify Q5 — real-time without polling; reuses 004/007 SSE infrastructure and admin's existing `DisplayStateService` connection.

**Alternatives considered**:
- HTTP polling — rejected (non-goal)
- Separate SSE endpoint — rejected (duplicate connections)
- Per-key delta events — rejected (≤5 keys; full snapshot simpler)

## Decision: REST snapshot endpoint

**Decision**: `GET /api/youtube/api-keys/usage` (operator auth) returns current list + `next_reset_at`.

**Rationale**: Initial admin paint before SSE events; recovery after reconnect.

**Alternatives considered**:
- SSE-only — rejected (no initial state on connect without extra server work; state stream already sends queue state first)

## Decision: Pacific quota day shared helper

**Decision**: Extract `pacific_quota_day()` / `next_pacific_midnight()` utility used by pool exhaustion and usage reset.

**Rationale**: FR-005 alignment with 008 `mark_exhausted` until Pacific midnight.

## Decision: Concurrency via row lock

**Decision**: `SELECT … FOR UPDATE` on usage row during `record_attempt`.

**Rationale**: Concurrent participant searches during events; prevents lost increments.

**Alternatives considered**:
- Application-level mutex — rejected (insufficient multi-worker)

## Decision: Admin UI placement and refresh

**Decision**: Dedicated **Uso de API Keys** section between Moderación and Evento; Spanish labels; global reset indicator; updates via SSE (clarify Q3–Q5).

**Rationale**: Spec clarifications; matches stacked admin sections pattern.

## Decision: Testing strategy

**Decision**:
- `test_youtube_api_key_usage.py`: increment, cap at 100, google exhausted sync, Pacific roll, auth 401, masked response
- Extend `test_youtube_search.py`: search increments correct key
- SSE: `collect_sse_events_after` pattern for `api_key_usage`
- Frontend: build + optional admin component unit test for table render

**Rationale**: Constitution V; SC-002–SC-006.

## Open questions

None blocking plan.
