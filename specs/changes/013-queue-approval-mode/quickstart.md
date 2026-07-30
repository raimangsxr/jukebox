# Quickstart: 013-queue-approval-mode

Validation after implementation.

## Prerequisites

- Changes 001–010 applied
- Operator session on `/admin`
- Participant session on `/participar` (Google OAuth or dev participant)
- Kiosk `/` open for queue visibility

## Phase 1 — Default Moderado (SC-003, SC-005 regression)

1. Fresh deploy or confirm `queue_mode` is `moderated` (`GET /api/event-config` as operator)
2. Participant submits a song → appears in **Moderación** pending table, **not** in kiosk queue
3. Operator approves → song in kiosk queue; participant toast «ha sido aprobada y está en cola»
4. Voting, skip, notifications unchanged vs pre-change baseline

## Phase 2 — Switch to Libre (SC-002, FR-006–FR-007)

1. On `/admin` → **Moderación** → selector shows **Moderado**
2. Select **Libre** → confirm dialog → confirm
3. Info message visible: new submissions skip review
4. Participant submits new song → **immediately** in kiosk queue (<5s, SC-002)
5. Pending table does **not** gain the new row
6. Participant sees «en cola» in Mis canciones + approval toast on submit (FR-016)

## Phase 2b — SC-002 timing gate

1. With stopwatch: from participant submit click to song visible in kiosk queue strip
2. Record elapsed time; must be **< 5 seconds** (SC-002)
3. Note result in PR or implementation notes for T026

## Phase 3 — Libre submission cap (FR-017)

1. With cap = 2 (default), participant queues 2 songs in Libre mode
2. Third submit → 429 `pending submission limit reached` (same message as moderated pending cap)

## Phase 3b — Duplicate video in Libre (FR-015)

1. With a video already `queued`, participant submits the same video again in Libre mode
2. Expect **409** `video already in queue` (same as Moderado)

## Phase 4 — Mode switch with legacy pendings (FR-008, FR-010)

1. Switch back to **Moderado**; submit → pending again
2. Switch to **Libre** with 1+ pending rows still open
3. Pending rows remain actionable (approve/reject)
4. **Reject** a legacy pending row while in Libre → entry `rejected`, not in queue (FR-008)
5. New submit in Libre → direct to queue only

## Phase 5 — Confirmation cancel (FR-019)

1. Select opposite mode → dialog → **Cancel**
2. Mode unchanged after reload; behavior unchanged

## Phase 6 — Auth & persistence (FR-003, FR-004)

1. `curl PUT /api/event-config/queue-mode` without cookie → 401
2. Set Libre → restart backend → reload admin → still **Libre**

## Phase 7 — No participant mode UI (FR-020)

1. `/participar` — no banner/badge for mode (visual inspection)

## Phase 8 — Automated

```bash
pytest backend/tests/test_queue_approval_mode.py
pytest backend/tests/test_participant_submit.py
pytest backend/tests/test_notifications.py
pytest backend/tests/test_queue.py
npm --prefix frontend run build
npm --prefix frontend test -- --include='**/event-config.service.spec.ts'
```

## Phase 9 — Usability gates (SC-001, SC-006)

1. **SC-001**: Ask a colleague (or self with fresh eyes) to find and change the mode in `/admin` without docs; record time (target < 30s)
2. **SC-006**: Brief guided review — can the reviewer state which mode is active after seeing the selector? (document pass/fail in PR notes)
3. Attach results to T026 completion notes

## Manual API probe

```bash
# Read mode (operator)
curl -s -b operator.txt http://localhost:8000/api/event-config | jq .queue_mode

# Set Libre
curl -s -X PUT -b operator.txt \
  -H 'Content-Type: application/json' \
  -d '{"queue_mode":"free"}' \
  http://localhost:8000/api/event-config/queue-mode | jq
```
