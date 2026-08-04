# Quickstart: 020-fill-queue-from-reserve

Validation after implementation. Requires **017** filler reserve + auto-inject toggle.

## Prerequisites

- Branch `020-fill-queue-from-reserve`
- Operator session on `/admin`
- Inyección automática **activada**
- At least 2 distinct YouTube videos for reserve

## Phase 1 — Playing + empty queued (US1, SC-001)

1. Enqueue one participant song → playing, no other `queued`
2. Add 1+ songs to **Reserva de relleno**
3. Trigger mutation (e.g. add another reserve song, or skip then re-queue until playing alone)
4. **Expected**: Kiosk strip shows ≥1 `queued` filler within 3s; `now_playing` unchanged
5. Participant `/participar` shows same queued filler; votable

## Phase 2 — Reserve add while playing (FR-009)

1. One song `playing`, zero `queued`, reserve empty
2. **Añadir playlist** or manual URL to reserve
3. **Expected**: First valid reserve song appears in `queued` without skip/advance

## Phase 3 — Duplicate skip removes reserve row (FR-007)

1. Song A `playing`, reserve position 1 = same video A, position 2 = video B
2. Trigger inject evaluation
3. **Expected**: A removed from reserve; B in `queued`; reserve shows only remaining items

## Phase 4 — Toggle on (clarification Q5)

1. Disable **Inyección automática**; playing + empty queued + reserve populated
2. Enable toggle
3. **Expected**: Immediate inject to `queued`

## Phase 5 — Toggle off / disabled (FR-006)

1. Disable inyección; playing + empty queued + reserve
2. Mutate reserve or skip
3. **Expected**: No inject; visible queue stays empty

## Phase 6 — Idle regression (US2, SC-002/003)

1. No `playing`, no `queued`, reserve populated
2. `POST /api/queue/skip` or idle auto-start path
3. **Expected**: Same as 017 — inject + auto-start playing

## Phase 7 — Passive read (clarification Q4)

1. Setup: playing + empty queued + reserve (inject disabled)
2. `GET /api/state` repeatedly
3. Enable inject in another session without mutation
4. **Expected**: GET alone does not inject until explicit mutation or toggle-on

## Automated

```bash
pytest backend/tests/test_filler_reserve.py -k "auto_inject or inject"
pytest backend/tests/test_queue.py backend/tests/test_state.py
npm --prefix frontend run build
```

## SC gates

| ID | Gate |
|----|------|
| SC-001 | playing + 0 queued + reserve → visible `queued` < 3s after mutation |
| SC-002 | Idle inject + auto-start timing unchanged vs baseline |
| SC-003 | All prior `test_auto_inject_*` pass |
| SC-004 | Manual kiosk strip no longer empty during playback with reserve |

Document results in PR notes.
