# Contract Deltas: 013-queue-approval-mode

**Status**: draft — merged into active contracts at implementation (change 013).

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, 001–010 behavior is unchanged.

---

## backend-api

### Event configuration — queue approval mode (new)

**`event_config` column** (migration `0009`): `queue_mode` `VARCHAR(16) NOT NULL DEFAULT 'moderated'` — values `moderated` | `free`.

**`EventConfigRead`** (operator `GET /api/event-config`): add `queue_mode: string`.

**`EventConfigSummary`** (in `StateResponse`, `ParticipantStateResponse`): **unchanged** — `queue_mode` is not exposed to kiosk or participant state payloads (FR-020).

### New endpoint

| Method | Path | Auth | Response |
|--------|------|------|----------|
| PUT | `/api/event-config/queue-mode` | operator session | 200 `EventConfigRead` |

Body: `QueueModeUpdate` — `{ "queue_mode": "moderated" | "free" }`.

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| Invalid `queue_mode` | 422 | validation error |
| Success | 200 | updated config; `bump_revision`; SSE `state` broadcast |

`PUT /api/event-config` (Evento form) does **not** accept `queue_mode`; mode changes only via `/api/event-config/queue-mode`.

### Participant submit — mode-dependent behavior (changes 004/006)

`POST /api/queue/submit` (participant auth):

| `queue_mode` | Created status | Pending list | Notification |
|--------------|----------------|--------------|--------------|
| `moderated` | `pending_review` | appears in `GET /api/queue/pending` | `song.approved` only on operator approve (unchanged) |
| `free` | `queued` (with position) | **not** in pending list | `song.approved` immediately on successful submit |

**Limits** (same env `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT`, default 2):

| Mode | Counted rows | 429 `detail` |
|------|--------------|--------------|
| `moderated` | participant `pending_review` | `pending submission limit reached` (unchanged) |
| `free` | participant `queued` | `pending submission limit reached` (same message) |

Duplicate video rule unchanged (`409 video already in queue`). Queue full (`409 queue is full`) applies when enqueueing in free mode.

Moderation `POST approve` / `POST reject` unchanged; still only valid for `pending_review` entries (including legacy pendings after switch to free).

Default on new DB / migration: `moderated`.

### Tests (constitution V)

- `backend/tests/test_queue_approval_mode.py` (new)
- Extend `test_participant_submit.py` / `test_notifications.py` as needed

---

## app-core

### Admin `/admin` — Moderación section (changes 004, 010)

**New control** above the pending review table (clarify Q2):

- Shows current mode with Spanish labels: **Moderado** / **Libre**
- Changing selection opens **confirmation dialog** before `PUT /api/event-config/queue-mode` (FR-019)
- On success, updates local `queueMode` from response; cancel leaves prior mode

**Libre mode copy**: when `queue_mode === 'free'`, show informational text that new submissions skip review (pending table may still list legacy `pending_review` rows).

**Evento section**: unchanged — does not edit `queue_mode`.

### Participar `/participar` (changes 006/007)

- **No** mode indicator banner (FR-020)
- Free submit: «Mis canciones» shows `queued`; toast ««{title}» ha sido aprobada y está en cola.» on submit (same as post-approve in moderated mode)
- Moderated submit: unchanged (`pending_review`, toast only after approve)

### Display `/` (kiosk)

- No UI change; free submissions appear in queue strip via existing SSE `state` updates

---

## ops-platform

No manifest, env, or topology changes. `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` semantics extended for free mode (document in backend-api contract table above).
