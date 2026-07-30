# Research: 013-queue-approval-mode

**Date**: 2026-07-30

## Decision: Persist mode on `event_config.queue_mode`

**Decision**: Alembic migration `0009` adds non-null `queue_mode` column to `event_config` with values `moderated` | `free`, default `moderated`.

**Rationale**: Mode is singleton per event (spec assumption); `event_config` already holds editable event settings (010); survives restarts (FR-004); existing bootstrap `ensure_event_config` pattern applies.

**Alternatives considered**:
- Env var only — rejected (not operator-editable from `/admin`)
- Separate `queue_settings` table — rejected (YAGNI for one enum field)
- `jukebox_runtime` column — rejected (runtime is revision/now-playing, not product config)

## Decision: Dedicated `PUT /api/event-config/queue-mode`

**Decision**: Operator-only endpoint with body `{ "queue_mode": "moderated" | "free" }`; returns `EventConfigRead` (includes `queue_mode`); bumps `revision` and broadcasts SSE `state`.

**Rationale**: Selector lives in **Moderación** (clarify Q2), decoupled from the **Evento** full-form `PUT /api/event-config`; avoids partial-update scope on the existing PUT; confirmation dialog maps to a single-purpose API call.

**Alternatives considered**:
- Extend `EventConfigUpdate` with `queue_mode` — rejected (moderation UX separate from Evento form; PUT requires all fields today)
- `PATCH /api/event-config` partial — rejected (broader API change than needed)

## Decision: `queue_mode` on `EventConfigRead` only, not `EventConfigSummary`

**Decision**: Add `queue_mode` to operator `EventConfigRead` / update DTO; **omit** from `EventConfigSummary` in `StateResponse` and `ParticipantStateResponse`.

**Rationale**: FR-020 — no participant-visible mode indicator; participants infer behavior from submit outcome; kiosk does not need mode; admin loads via `GET /api/event-config` (already used for Evento section).

**Alternatives considered**:
- Include in `EventConfigSummary` — rejected (unnecessary exposure on `/participar` state JSON)

## Decision: Branch `submit_as_participant` by mode

**Decision**:
- **`moderated`**: current path — `pending_review`, limit counts `pending_review` rows (unchanged).
- **`free`**: create entry as `queued` with `approved_at`, `position`, `_recompute_positions`, `emit_song_approved`, limit counts participant `queued` rows (clarify Q1).

**Rationale**: Single code path reuse via internal `_enqueue_approved_entry` extracted from `approve_entry`; notifications and kiosk queue update match approve semantics (FR-016).

**Alternatives considered**:
- Create `pending_review` then auto-approve in same transaction — rejected (violates FR-007, pollutes pending list)

## Decision: Spanish UI labels, English API enum

**Decision**: API/DB values `moderated` / `free`; admin UI labels **Moderado** / **Libre** (constitution: Spanish user-facing).

**Rationale**: Consistent with existing `QueueEntryStatus` English enum values and Spanish admin copy.

## Decision: Mode change does not mutate existing entries

**Decision**: `PUT queue-mode` only updates config + `bump_revision`; no bulk approve/reject (FR-009, FR-010, clarify pending behavior).

**Rationale**: Spec acceptance scenarios; lowest risk during live events.

## Decision: Admin confirmation in frontend only

**Decision**: Native `confirm()` or small inline modal before `PUT`; cancel leaves UI unchanged (FR-019).

**Rationale**: No backend “draft mode” needed; operator session already required.

**Alternatives considered**:
- Two-step server token — rejected (over-engineering)

## Decision: Test module `test_queue_approval_mode.py`

**Decision**: New pytest file covering moderated regression, free direct enqueue, free queued cap, mode endpoint auth, notification on free submit; extend participant submit tests where needed.

**Rationale**: Constitution V; isolates new behavior from large `test_queue.py`.
