# Data Model: 022-limit-reset-countdown

**Feature**: `022-limit-reset-countdown`  
**Migration**: Yes (Alembic)

## Schema changes

### `participants` (alter)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `votes_quota_reset_at` | `timestamptz` | YES | End of active vote window; `NULL` = no window (full quota, no countdown) |
| `searches_quota_reset_at` | `timestamptz` | YES | End of active search window; `NULL` = no window |

**Rules**:
- Set on **first consumption at full quota** to `now_utc + WINDOW` (10 min default from settings).
- Additional consumptions in window **do not** update the column.
- On any limit read, if `now_utc >= *_quota_reset_at`, set column to `NULL` (window expired).

### `participant_searches` (new)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `varchar(36)` | PK | UUID |
| `participant_id` | `varchar(36)` | FK → `participants.id` ON DELETE CASCADE, index | Owner |
| `created_at` | `timestamptz` | NOT NULL, default now() | Successful search timestamp |

**Index**: `(participant_id, created_at)` for in-window counts.

## Derived fields (API, not stored)

On `ParticipantStateResponse`:

| Field | Type | When set |
|-------|------|----------|
| `votes_remaining` | int | `max_votes − count(votes in window)` or `max` if no window |
| `searches_remaining` | int | `max_searches − count(participant_searches in window)` or `max` |
| `votes_quota_reset_at` | ISO datetime \| null | Non-null iff window active (≥1 vote consumed, not yet expired) |
| `searches_quota_reset_at` | ISO datetime \| null | Non-null iff window active (≥1 search consumed, not yet expired) |

**Countdown visibility** (client): show «Cupo completo en MM:SS» iff corresponding `*_quota_reset_at` is non-null **and** `now < reset_at`. Server sets `reset_at` on first full-quota consumption; clears on expiry — equivalent to spec FR-004 («from first consume until full recovery»).

## Window lifecycle

```text
[Full quota, no window]
    │ first vote/search at full quota
    ▼
[Window active]  *_quota_reset_at = T0 + 10min
    │ consume up to max in window; countdown fixed to reset_at
    ▼
[now >= reset_at]  clear column → full quota restored
    │
    └──► back to [Full quota, no window]
```

## Entities (logical)

- **Vote window**: `participants.votes_quota_reset_at` + `votes` rows in `[reset_at − WINDOW, reset_at)`
- **Search window**: `participants.searches_quota_reset_at` + `participant_searches` rows in same interval
- **WINDOW duration**: `settings.max_*_10minutes` env (unchanged); duration from `timedelta(minutes=10)` constant aligned with 016

## Unchanged

- `votes` table structure (Vote rows still record each cast)
- `max_pending_submissions` (not window-based)
- Operator YouTube search bypass (no participant session → no limit)

## Validation rules

- Invalid search / failed vote → no `participant_searches` row / no Vote row → no window start
- Paste URL submit → does not touch search window
- `votes_quota_reset_at` only set when `votes_remaining == max` **before** consuming
